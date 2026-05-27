import json
import os
import re
import ast
import requests
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app import models
from backend.app.prompts.phase_prompts import build_system_prompt, build_phase_user_prompt

settings = get_settings()

FIREWORKS_API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"


class AIService:
    def __init__(self, db: Session):
        self.db = db

    def _phase_label(self, phase_number: int) -> str:
        phase_names = {
            0: "Project Setup",
            1: "Upfront Decisions",
            2: "Familiarisation Notes",
            3: "Codebook",
            4: "Candidate Themes",
            5: "Refined Themes",
            6: "Final Themes",
            7: "Manuscript Report",
        }
        return phase_names.get(phase_number, f"Phase {phase_number} Output")

    def _extract_assistant_text_from_transcript(self, transcript: Optional[str]) -> str:
        if not transcript:
            return ""
        try:
            payload = json.loads(transcript)
        except (TypeError, ValueError):
            return ""
        if not isinstance(payload, list):
            return ""

        assistant_chunks = []
        for message in payload:
            if not isinstance(message, dict):
                continue
            if message.get("role") != "assistant":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                assistant_chunks.append(content.strip())
        return "\n\n".join(assistant_chunks)

    def _state_to_structured_dict(self, state: Optional[models.PhaseState]) -> Dict[str, Any]:
        if not state:
            return {}

        normalized = self._normalize_structured_data(state.phase_number, state.structured_data)
        if normalized:
            return normalized

        assistant_text = self._extract_assistant_text_from_transcript(state.ai_transcript)
        if not assistant_text:
            return {}

        parsed = self._extract_json(assistant_text)
        recovered = self._normalize_structured_data(state.phase_number, parsed)
        return recovered or {}

    def _get_project_context(self, project: models.Project, phase_number: Optional[int] = None) -> Dict[str, Any]:
        effective_phase = phase_number if phase_number is not None else (project.current_phase or 0)

        previous_states = (
            self.db.query(models.PhaseState)
            .filter(models.PhaseState.project_id == project.id)
            .filter(models.PhaseState.phase_number < effective_phase)
            .order_by(models.PhaseState.phase_number.asc())
            .all()
        )
        for state in previous_states:
            try:
                self.save_phase_data_to_file(
                    project,
                    state.phase_number,
                    self._state_to_structured_dict(state),
                    response_text=self._extract_assistant_text_from_transcript(state.ai_transcript),
                )
            except Exception as e:
                print(f"Could not backfill phase output source for phase {state.phase_number}: {e}")

        user_sources = []
        system_outputs = []
        all_sources = (
            self.db.query(models.Source)
            .filter(models.Source.project_id == project.id)
            .order_by(models.Source.created_at.asc())
            .all()
        )
        for s in all_sources:
            src_dict = {"id": s.id, "name": s.name, "source_type": s.source_type, "content": s.content}
            if s.source_type == "phase_output":
                system_outputs.append(src_dict)
            else:
                user_sources.append(src_dict)

        prior_structured = {}
        if effective_phase > 0:
            prev_state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == effective_phase - 1)
                .first()
            )
            prior_structured = self._state_to_structured_dict(prev_state)

        current_state = (
            self.db.query(models.PhaseState)
            .filter(models.PhaseState.project_id == project.id)
            .filter(models.PhaseState.phase_number == effective_phase)
            .first()
        )
        current_structured = self._state_to_structured_dict(current_state)

        return {
            "research_question": project.research_question,
            "analytic_decisions": project.analytic_decisions or {},
            "sources": user_sources,
            "system_outputs": system_outputs,
            "current_phase": effective_phase,
            "prior_structured_data": prior_structured,
            "current_structured_data": current_structured,
        }

    def _extract_json(self, text: str) -> Optional[Any]:
        """Extract JSON-like content from assistant output and parse it robustly."""
        if not text:
            return None

        def clean_json_string(raw: str) -> str:
            raw = re.sub(r"//.*$", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
            raw = re.sub(r",\s*([\]}])", r"\1", raw)
            return raw.strip()

        def parse_candidate(candidate: str) -> Optional[Any]:
            cleaned = clean_json_string(candidate)
            if not cleaned:
                return None
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            try:
                parsed = ast.literal_eval(cleaned)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except (ValueError, SyntaxError):
                return None
            return None

        def iter_balanced_json_candidates(raw: str):
            length = len(raw)
            for start in range(length):
                if raw[start] not in "{[":
                    continue
                stack = []
                in_string = False
                escaping = False
                for idx in range(start, length):
                    ch = raw[idx]
                    if in_string:
                        if escaping:
                            escaping = False
                        elif ch == "\\":
                            escaping = True
                        elif ch == "\"":
                            in_string = False
                        continue
                    if ch == "\"":
                        in_string = True
                        continue
                    if ch in "{[":
                        stack.append(ch)
                    elif ch in "}]":
                        if not stack:
                            break
                        opener = stack.pop()
                        if (opener == "{" and ch != "}") or (opener == "[" and ch != "]"):
                            break
                        if not stack:
                            yield raw[start: idx + 1]
                            break

        fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        for block in fenced_blocks:
            parsed = parse_candidate(block)
            if parsed is not None:
                return parsed

        for candidate in iter_balanced_json_candidates(text):
            parsed = parse_candidate(candidate)
            if parsed is not None:
                return parsed

        return None

    def _normalize_structured_data(self, phase_number: int, raw_data: Any) -> Optional[Dict[str, Any]]:
        if raw_data is None:
            return None

        if isinstance(raw_data, str):
            candidate = raw_data.strip()
            if candidate:
                parsed: Optional[Any] = None
                try:
                    parsed = json.loads(candidate)
                except (TypeError, ValueError):
                    try:
                        parsed = ast.literal_eval(candidate)
                    except (ValueError, SyntaxError):
                        parsed = None
                if parsed is not None:
                    return self._normalize_structured_data(phase_number, parsed)

        normalized: Optional[Dict[str, Any]] = None

        if isinstance(raw_data, dict):
            normalized = raw_data
        elif isinstance(raw_data, list):
            if phase_number == 2:
                if all(isinstance(item, str) for item in raw_data):
                    normalized = {"initial_ideas": raw_data}
                else:
                    normalized = {"source_notes": raw_data}
            elif phase_number == 3:
                normalized = {"codes": raw_data}
            elif phase_number == 4:
                normalized = {"candidate_themes": raw_data}
            elif phase_number == 5:
                normalized = {"refined_themes": raw_data}
            elif phase_number == 6:
                normalized = {"final_themes": raw_data}
            elif phase_number == 7:
                if all(isinstance(item, str) for item in raw_data):
                    normalized = {"report_text": "\n".join(raw_data)}
                else:
                    normalized = {"extracts_for_report": raw_data}
        elif isinstance(raw_data, str) and phase_number == 7:
            if raw_data.strip():
                normalized = {"report_text": raw_data.strip()}

        if normalized is None:
            return None

        try:
            healed = heal_structured_data(phase_number, normalized)
            return healed if isinstance(healed, dict) else normalized
        except Exception:
            return normalized

    def run_phase_chat(
        self,
        project: models.Project,
        phase_number: int,
        messages: list,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        if not settings.fireworks_api_key:
            return (
                "FIREWORKS_API_KEY is not configured. Please set it in your environment variables to use AI-guided analysis.",
                None,
            )

        system_prompt = build_system_prompt(phase_number)

        if len(messages) == 1 and messages[0].get("role") == "user":
            context = self._get_project_context(project, phase_number)
            phase_prompt = build_phase_user_prompt(phase_number, context)
            messages[0]["content"] = f"{messages[0]['content']}\n\n{phase_prompt}" if messages[0]["content"] else phase_prompt

        payload = {
            "model": settings.fireworks_model,
            "max_tokens": 12000,
            "top_p": 1,
            "top_k": 40,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "temperature": 0.6,
            "messages": [
                {"role": "system", "content": system_prompt},
                *[{"role": m["role"], "content": m["content"]} for m in messages],
            ],
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.fireworks_api_key}",
        }

        try:
            response = requests.post(FIREWORKS_API_URL, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
        except requests.RequestException as exc:
            return (f"AI request failed: {exc}", None)

        response_data = response.json()
        response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        structured_data = self._normalize_structured_data(
            phase_number,
            self._extract_json(response_text)
        )

        transcript = json.dumps(messages + [{"role": "assistant", "content": response_text}])

        phase_state = (
            self.db.query(models.PhaseState)
            .filter(models.PhaseState.project_id == project.id)
            .filter(models.PhaseState.phase_number == phase_number)
            .first()
        )

        if phase_state:
            phase_state.ai_transcript = transcript
            if structured_data:
                phase_state.structured_data = structured_data
            phase_state.updated_at = __import__("datetime").datetime.utcnow()
        else:
            phase_state = models.PhaseState(
                project_id=project.id,
                phase_number=phase_number,
                ai_transcript=transcript,
                structured_data=structured_data,
            )
            self.db.add(phase_state)

        # Sync upfront decisions for Phase 1 directly to the project model for persistence
        if phase_number == 1 and structured_data:
            decisions = project.analytic_decisions or {}
            
            def find_val(d, key):
                if not isinstance(d, dict):
                    return None
                if key in d:
                    return d[key]
                for k, v in d.items():
                    if isinstance(v, dict):
                        res = find_val(v, key)
                        if res is not None:
                            return res
                return None

            for key in ["scope", "coding_approach", "theme_level", "epistemology"]:
                val = find_val(structured_data, key)
                if val:
                    decisions[key] = val
            
            project.analytic_decisions = decisions

        self.db.commit()

        # Write phase outputs as physical files and phase memory sources for downstream phases.
        try:
            self.save_phase_data_to_file(project, phase_number, structured_data, response_text=response_text)
            if structured_data:
                self.sync_structured_data_to_db(project, phase_number, structured_data)
        except Exception as e:
            print(f"Error saving/syncing phase data: {e}")

        return response_text, structured_data

    def validate_phase_data(self, project: models.Project, phase_number: int) -> Tuple[bool, list]:
        """Programmatically validate that the required qualitative data for the given phase has been generated and saved."""
        errors = []
        
        # Normalize existing structured data into a safe dict shape for the validator
        state = (
            self.db.query(models.PhaseState)
            .filter(models.PhaseState.project_id == project.id)
            .filter(models.PhaseState.phase_number == phase_number)
            .first()
        )
        if state and state.structured_data:
            try:
                normalized = self._normalize_structured_data(phase_number, state.structured_data)
                if normalized is None:
                    return False, [
                        "Saved structured data for this phase is malformed. Please regenerate this phase output."
                    ]
                state.structured_data = normalized
                self.db.commit()
            except Exception as e:
                print(f"Error healing state during validation: {e}")
        
        if phase_number == 0:
            if not project.sources:
                errors.append("No sources have been uploaded yet. Please upload at least one transcript or document file.")
            
        elif phase_number == 1:
            decisions = project.analytic_decisions or {}
            required_keys = ["scope", "coding_approach", "theme_level", "epistemology"]
            
            # Sync decisions from state if not populated on project
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 1)
                .first()
            )
            
            if state and state.structured_data:
                def find_val(d, key):
                    if not isinstance(d, dict):
                        return None
                    if key in d:
                        return d[key]
                    for k, v in d.items():
                        if isinstance(v, dict):
                            res = find_val(v, key)
                            if res is not None:
                                return res
                    return None

                updated = False
                for k in required_keys:
                    if not decisions.get(k):
                        val = find_val(state.structured_data, k)
                        if val:
                            decisions[k] = val
                            updated = True
                if updated:
                    project.analytic_decisions = decisions
                    self.db.commit()
                    
            missing = [k for k in required_keys if not decisions.get(k)]
            if missing:
                errors.append(f"Missing upfront analytic decisions: {', '.join(missing)}")
                
        elif phase_number == 2:
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 2)
                .first()
            )
            if not state or not state.structured_data:
                errors.append("No familiarisation notes have been saved yet.")
            else:
                data = state.structured_data
                if not data.get("source_notes"):
                    errors.append("Missing 'source_notes' array.")
                elif not isinstance(data["source_notes"], list) or len(data["source_notes"]) == 0:
                    errors.append("'source_notes' must be a non-empty array.")
                else:
                    normalized_notes = []
                    for idx, sn in enumerate(data["source_notes"]):
                        if not isinstance(sn, dict):
                            errors.append(f"Familiarisation summary {idx} is not a valid JSON object.")
                            continue
                        
                        source_name = sn.get("name") or sn.get("source_name") or sn.get("source") or sn.get("title") or sn.get("file_name")
                        source_summary = sn.get("summary") or sn.get("notes") or sn.get("note") or sn.get("content")
                        
                        if not source_name or not source_summary:
                            errors.append(f"Familiarisation summary {idx} is missing 'name' or 'summary'.")
                        else:
                            sn["name"] = source_name
                            sn["summary"] = source_summary
                            normalized_notes.append(sn)
                    
                    if not errors:
                        data["source_notes"] = normalized_notes
                        state.structured_data = data
                        self.db.commit()
                            
                if not data.get("initial_ideas"):
                    errors.append("Missing 'initial_ideas' array.")
                elif not isinstance(data["initial_ideas"], list) or len(data["initial_ideas"]) == 0:
                    errors.append("'initial_ideas' must be a non-empty array.")

        elif phase_number == 3:
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 3)
                .first()
            )
            if not state or not state.structured_data:
                errors.append("No initial coding has been completed.")
            else:
                data = state.structured_data
                if not data.get("codes"):
                    errors.append("Missing 'codes' array.")
                elif not isinstance(data["codes"], list) or len(data["codes"]) == 0:
                    errors.append("'codes' must be a non-empty array.")
                else:
                    normalized_codes = []
                    for idx, c in enumerate(data["codes"]):
                        if not isinstance(c, dict):
                            errors.append(f"Code item {idx} is not a valid JSON object.")
                            continue
                        
                        code_name = c.get("name") or c.get("code") or c.get("code_name")
                        code_definition = c.get("definition") or c.get("description") or c.get("meaning") or ""
                        code_extracts = c.get("extracts") or c.get("quotes") or c.get("examples") or c.get("citations")
                        
                        if not code_name:
                            errors.append(f"Code item {idx} is missing a code name.")
                        elif not code_extracts or not isinstance(code_extracts, list) or len(code_extracts) == 0:
                            errors.append(f"Code '{code_name or idx}' is missing its extracts list.")
                        else:
                            normalized_extracts = []
                            for ex_idx, ext in enumerate(code_extracts):
                                if isinstance(ext, dict):
                                    ext_text = ext.get("text") or ext.get("quote") or ext.get("extract") or ext.get("content")
                                    ext_src = ext.get("source_name") or ext.get("source") or ext.get("file")
                                    ext_context = ext.get("context") or ext.get("surrounding") or ""
                                    
                                    if ext_text:
                                        normalized_extracts.append({
                                            "text": ext_text,
                                            "source_name": ext_src or "Unknown Source",
                                            "context": ext_context
                                        })
                            
                            c["name"] = code_name
                            c["definition"] = code_definition
                            c["extracts"] = normalized_extracts
                            normalized_codes.append(c)
                            
                    if not errors:
                        data["codes"] = normalized_codes
                        state.structured_data = data
                        self.db.commit()
                            
        elif phase_number == 4:
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 4)
                .first()
            )
            if not state or not state.structured_data:
                errors.append("No candidate themes have been saved yet.")
            else:
                data = state.structured_data
                if not data.get("candidate_themes"):
                    errors.append("Missing 'candidate_themes' array.")
                elif not isinstance(data["candidate_themes"], list) or len(data["candidate_themes"]) == 0:
                    errors.append("'candidate_themes' must be a non-empty array.")
                else:
                    normalized_themes = []
                    for idx, t in enumerate(data["candidate_themes"]):
                        if not isinstance(t, dict):
                            errors.append(f"Candidate theme item {idx} is not a valid JSON object.")
                            continue
                        
                        theme_name = t.get("name") or t.get("theme") or t.get("theme_name")
                        theme_def = t.get("definition") or t.get("description") or ""
                        theme_type = t.get("type") or t.get("theme_type") or "overarching"
                        parent_name = t.get("parent_name") or t.get("parent") or ""
                        code_names = t.get("code_names") or t.get("codes") or t.get("associated_codes") or []
                        
                        if not theme_name:
                            errors.append(f"Candidate theme item {idx} is missing a theme name.")
                        else:
                            t["name"] = theme_name
                            t["definition"] = theme_def
                            t["type"] = theme_type
                            t["parent_name"] = parent_name
                            t["code_names"] = code_names
                            normalized_themes.append(t)
                            
                    if not errors:
                        data["candidate_themes"] = normalized_themes
                        state.structured_data = data
                        self.db.commit()
                            
        elif phase_number == 5:
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 5)
                .first()
            )
            if not state or not state.structured_data:
                errors.append("No refined themes have been saved yet.")
            else:
                data = state.structured_data
                if not data.get("refined_themes"):
                    errors.append("Missing 'refined_themes' array.")
                elif not isinstance(data["refined_themes"], list) or len(data["refined_themes"]) == 0:
                    errors.append("'refined_themes' must be a non-empty array.")
                else:
                    normalized_themes = []
                    for idx, t in enumerate(data["refined_themes"]):
                        if not isinstance(t, dict):
                            errors.append(f"Refined theme item {idx} is not a valid JSON object.")
                            continue
                        
                        theme_name = t.get("name") or t.get("theme") or t.get("theme_name")
                        theme_def = t.get("definition") or t.get("description") or ""
                        theme_type = t.get("type") or t.get("theme_type") or "overarching"
                        parent_name = t.get("parent_name") or t.get("parent") or ""
                        code_names = t.get("code_names") or t.get("codes") or t.get("associated_codes") or []
                        
                        if not theme_name:
                            errors.append(f"Refined theme item {idx} is missing a theme name.")
                        else:
                            t["name"] = theme_name
                            t["definition"] = theme_def
                            t["type"] = theme_type
                            t["parent_name"] = parent_name
                            t["code_names"] = code_names
                            normalized_themes.append(t)
                            
                    if not errors:
                        data["refined_themes"] = normalized_themes
                        state.structured_data = data
                        self.db.commit()

        elif phase_number == 6:
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 6)
                .first()
            )
            if not state or not state.structured_data:
                errors.append("No final named themes have been saved.")
            else:
                data = state.structured_data
                if not data.get("final_themes"):
                    errors.append("Missing 'final_themes' array.")
                elif not isinstance(data["final_themes"], list) or len(data["final_themes"]) == 0:
                    errors.append("'final_themes' must be a non-empty array.")
                else:
                    normalized_themes = []
                    for idx, t in enumerate(data["final_themes"]):
                        if not isinstance(t, dict):
                            errors.append(f"Final theme item {idx} is not a valid JSON object.")
                            continue
                        
                        theme_name = t.get("name") or t.get("theme") or t.get("theme_name")
                        theme_def = t.get("definition") or t.get("description") or ""
                        theme_type = t.get("type") or t.get("theme_type") or "overarching"
                        parent_name = t.get("parent_name") or t.get("parent") or ""
                        sub_themes = t.get("sub_themes") or []
                        
                        if not theme_name:
                            errors.append(f"Final theme item {idx} is missing a theme name.")
                        else:
                            t["name"] = theme_name
                            t["definition"] = theme_def
                            t["type"] = theme_type
                            t["parent_name"] = parent_name
                            t["sub_themes"] = sub_themes
                            normalized_themes.append(t)
                            
                    if not errors:
                        data["final_themes"] = normalized_themes
                        state.structured_data = data
                        self.db.commit()
                if not data.get("synopsis"):
                    errors.append("Missing narrative 'synopsis' of themes.")

        elif phase_number == 7:
            state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == 7)
                .first()
            )
            if not state or not state.structured_data:
                errors.append("No final report manuscript text has been saved.")
            else:
                data = state.structured_data
                if not data.get("report_text") or len(str(data["report_text"]).strip()) < 100:
                    errors.append("Final report manuscript text ('report_text') is missing or too brief.")

        return len(errors) == 0, errors

    def save_phase_data_to_file(
        self,
        project: models.Project,
        phase_number: int,
        structured_data: Optional[Dict[str, Any]],
        response_text: Optional[str] = None,
    ):
        """Persist phase outputs as physical files and source memory used by later phases."""
        phase_label = self._phase_label(phase_number)
        normalized = self._normalize_structured_data(phase_number, structured_data) if structured_data else None

        md_content = structured_data_to_markdown(phase_number, normalized) if normalized else ""
        if not md_content.strip() and response_text and response_text.strip():
            md_content = f"# {phase_label}\n\n{response_text.strip()}\n"
        if not md_content.strip():
            return

        # Write MD file
        md_filename = f"{project.id}_phase_{phase_number}_output.md"
        md_path = os.path.join(settings.uploads_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Write JSON file when structured output exists
        if normalized:
            json_filename = f"{project.id}_phase_{phase_number}_output.json"
            json_path = os.path.join(settings.uploads_dir, json_filename)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(normalized, f, indent=2)

        # Check if the Source record already exists for this system phase output
        db_source = (
            self.db.query(models.Source)
            .filter(models.Source.project_id == project.id)
            .filter(models.Source.source_type == "phase_output")
            .filter(models.Source.name == f"System - {phase_label}")
            .first()
        )

        if db_source:
            db_source.content = md_content
            db_source.file_path = md_path
        else:
            db_source = models.Source(
                project_id=project.id,
                name=f"System - {phase_label}",
                source_type="phase_output",
                content=md_content,
                file_path=md_path
            )
            self.db.add(db_source)

        self.db.commit()

    def sync_structured_data_to_db(self, project: models.Project, phase_number: int, data: Dict[str, Any]):
        """Synchronize the AI-generated structured data directly to the relational database tables 
        (codes, extracts, themes) to ensure the data is fully saved and structurally secure."""
        if not data:
            return
            
        if phase_number == 3:
            # Sync Phase 3 Codebook to Codes & Extracts tables
            codes_list = data.get("codes", [])
            if not isinstance(codes_list, list):
                return
                
            # Wiping existing extracts for all project sources
            source_ids = [s.id for s in project.sources]
            if source_ids:
                self.db.query(models.Extract).filter(models.Extract.source_id.in_(source_ids)).delete(synchronize_session=False)
            # Wipe existing codes
            self.db.query(models.Code).filter(models.Code.project_id == project.id).delete(synchronize_session=False)
            self.db.commit()
            
            for c in codes_list:
                if not isinstance(c, dict) or not c.get("name"):
                    continue
                db_code = models.Code(
                    project_id=project.id,
                    name=c["name"],
                    definition=c.get("definition", ""),
                    color=c.get("color", "#6366f1")
                )
                self.db.add(db_code)
                
                extracts = c.get("extracts", [])
                if isinstance(extracts, list):
                    for ext in extracts:
                        if not isinstance(ext, dict) or not ext.get("text"):
                            continue
                        # Find matching source
                        source = next((s for s in project.sources if s.name.lower() == ext.get("source_name", "").lower()), None)
                        if not source and project.sources:
                            source = project.sources[0]
                        if source:
                            db_extract = models.Extract(
                                source_id=source.id,
                                text=ext["text"],
                                context=ext.get("context", "")
                            )
                            db_extract.codes.append(db_code)
                            self.db.add(db_extract)
            self.db.commit()
            
        elif phase_number in (4, 5, 6):
            # Sync Phase 4/5/6 Themes to Themes table
            expected_key = "candidate_themes" if phase_number == 4 else "refined_themes" if phase_number == 5 else "final_themes"
            themes_list = data.get(expected_key, [])
            if not isinstance(themes_list, list):
                return
                
            # Wipe existing themes for this project
            self.db.query(models.Theme).filter(models.Theme.project_id == project.id).delete(synchronize_session=False)
            self.db.commit()
            
            # Get existing codes to link them to themes
            db_codes = self.db.query(models.Code).filter(models.Code.project_id == project.id).all()
            code_map = {c.name.lower(): c for c in db_codes}
            
            inserted_themes = []
            theme_list_normalized = []
            
            for t in themes_list:
                if not isinstance(t, dict) or not t.get("name"):
                    continue
                db_theme = models.Theme(
                    project_id=project.id,
                    name=t["name"],
                    definition=t.get("definition", ""),
                    theme_type=t.get("type") or t.get("theme_type") or "overarching"
                )
                self.db.add(db_theme)
                inserted_themes.append(db_theme)
                theme_list_normalized.append(t)
                
                # Link associated codes
                code_names = t.get("code_names") or t.get("codes") or []
                if isinstance(code_names, list):
                    for c_name in code_names:
                        if isinstance(c_name, str):
                            code_obj = code_map.get(c_name.lower())
                            if code_obj:
                                db_theme.codes.append(code_obj)
            
            self.db.commit()
            
            # Update parent-child subtheme relationships if parent_name is specified
            theme_map = {t.name: t for t in inserted_themes}
            updated = False
            for t in theme_list_normalized:
                parent_name = t.get("parent_name") or t.get("parent")
                if parent_name:
                    theme_obj = theme_map.get(t["name"])
                    parent_obj = theme_map.get(parent_name)
                    if theme_obj and parent_obj:
                        theme_obj.parent_id = parent_obj.id
                        updated = True
            if updated:
                self.db.commit()



def structured_data_to_markdown(phase_number: int, data: Dict[str, Any]) -> str:
    if not data:
        return ""
        
    md = ""
    if phase_number == 1:
        md += "# Phase 1 Upfront Decisions\n\n"
        md += f"- **Scope**: {data.get('scope', 'N/A')}\n"
        md += f"- **Coding Approach**: {data.get('coding_approach', 'N/A')}\n"
        md += f"- **Theme Level**: {data.get('theme_level', 'N/A')}\n"
        md += f"- **Epistemology**: {data.get('epistemology', 'N/A')}\n\n"
        if data.get("method_statement"):
            md += "## Method Statement\n"
            md += f"{data.get('method_statement')}\n"
            
    elif phase_number == 2:
        md += "# Phase 2 Familiarisation Notes\n\n"
        if data.get("source_notes"):
            md += "## Source Summaries\n\n"
            for note in data["source_notes"]:
                md += f"### {note.get('name', 'Source')}\n"
                md += f"{note.get('summary', '')}\n\n"
        if data.get("initial_ideas"):
            md += "## Initial Ideas / Hunches\n\n"
            for idea in data["initial_ideas"]:
                md += f"- {idea}\n"
                
    elif phase_number == 3:
        md += "# Phase 3 Codebook\n\n"
        if data.get("codes"):
            for code in data["codes"]:
                md += f"## Code: {code.get('name')}\n"
                md += f"**Definition**: {code.get('definition', 'N/A')}\n\n"
                md += "### Extracts:\n"
                for ext in code.get("extracts", []):
                    md += f"- *\"{ext.get('text', '')}\"* (Source: {ext.get('source_name', 'N/A')})\n"
                md += "\n"
        if data.get("coding_notes"):
            md += f"## Coding Notes\n{data.get('coding_notes')}\n"
            
    elif phase_number == 4:
        md += "# Phase 4 Candidate Themes\n\n"
        if data.get("candidate_themes"):
            for theme in data["candidate_themes"]:
                md += f"## Candidate Theme: {theme.get('name')}\n"
                md += f"- **Type**: {theme.get('type', 'overarching')}\n"
                if theme.get("parent_name"):
                    md += f"- **Parent**: {theme.get('parent_name')}\n"
                md += f"- **Definition**: {theme.get('definition', 'N/A')}\n"
                if theme.get("code_names"):
                    md += f"- **Associated Codes**: {', '.join(theme.get('code_names', []))}\n\n"
        if data.get("map_description"):
            md += f"## Thematic Map Description\n{data.get('map_description')}\n"
            
    elif phase_number == 5:
        md += "# Phase 5 Refined Themes\n\n"
        if data.get("refined_themes"):
            for theme in data["refined_themes"]:
                md += f"## Refined Theme: {theme.get('name')}\n"
                md += f"- **Type**: {theme.get('type', 'overarching')}\n"
                if theme.get("parent_name"):
                    md += f"- **Parent**: {theme.get('parent_name')}\n"
                md += f"- **Definition**: {theme.get('definition', 'N/A')}\n"
                if theme.get("code_names"):
                    md += f"- **Associated Codes**: {', '.join(theme.get('code_names', []))}\n\n"
        if data.get("review_notes"):
            md += f"## Review Decisions Summary\n{data.get('review_notes')}\n"
            
    elif phase_number == 6:
        md += "# Phase 6 Final Defined Themes\n\n"
        if data.get("final_themes"):
            for theme in data["final_themes"]:
                md += f"## Final Theme: {theme.get('name')}\n"
                md += f"- **Type**: {theme.get('type', 'overarching')}\n"
                if theme.get("parent_name"):
                    md += f"- **Parent**: {theme.get('parent_name')}\n"
                md += f"- **Definition**: {theme.get('definition', 'N/A')}\n\n"
        if data.get("synopsis"):
            md += f"## Overall Story Synopsis\n{data.get('synopsis')}\n"
            
    elif phase_number == 7:
        md += "# Phase 7 Final Analysis Report\n\n"
        md += f"{data.get('report_text', '')}\n"
        
    return md


def heal_structured_data(phase_number: int, data: dict) -> dict:
    """Intelligently analyze the structural shape of any arbitrary JSON returned by the AI,
    mapping completely different key names to standard database fields automatically based on data types."""
    if not isinstance(data, dict):
        return data
        
    lists = {k: v for k, v in data.items() if isinstance(v, list)}
    
    # Pre-heal: convert dictionary summaries of sources to list format if necessary
    for k, v in list(data.items()):
        if isinstance(v, dict) and k not in ["analytic_decisions", "prior_structured_data", "current_structured_data"]:
            # If a dict contains string keys and values, it is a source name -> summary map!
            if all(isinstance(kk, str) for kk in v.keys()) and len(v) > 0:
                converted = []
                for name, summary_val in v.items():
                    if isinstance(summary_val, str):
                        converted.append({"name": name, "summary": summary_val})
                    elif isinstance(summary_val, dict):
                        summary_val["name"] = name
                        converted.append(summary_val)
                if converted:
                    data["source_notes"] = converted
                    # refresh list caches
                    lists = {k2: v2 for k2, v2 in data.items() if isinstance(v2, list)}
                    break

    if phase_number == 2:
        source_notes_key = None
        initial_ideas_key = None
        
        for k, v in lists.items():
            if len(v) > 0:
                if isinstance(v[0], str):
                    initial_ideas_key = k
                elif isinstance(v[0], dict):
                    source_notes_key = k
                    
        if source_notes_key and source_notes_key != "source_notes":
            data["source_notes"] = data.pop(source_notes_key)
        if initial_ideas_key and initial_ideas_key != "initial_ideas":
            data["initial_ideas"] = data.pop(initial_ideas_key)
            
        # Hardened key alignment for source_notes inside Phase 2
        if "source_notes" in data and isinstance(data["source_notes"], list):
            for sn in data["source_notes"]:
                if isinstance(sn, dict):
                    # name
                    name_key = None
                    for k in sn.keys():
                        if any(x in k.lower() for x in ["name", "file", "title", "transcript", "participant", "doc", "source"]):
                            name_key = k
                            break
                    # summary
                    summary_key = None
                    for k in sn.keys():
                        if any(x in k.lower() for x in ["summary", "note", "content", "description", "obs", "find", "reflect", "analys", "insight"]):
                            summary_key = k
                            break
                    # Fallback based on value lengths
                    if not name_key or not summary_key:
                        string_keys = [k for k, val in sn.items() if isinstance(val, str)]
                        if len(string_keys) >= 2:
                            sorted_keys = sorted(string_keys, key=lambda sk: len(sn[sk]))
                            if not name_key:
                                name_key = sorted_keys[0]
                            if not summary_key:
                                summary_key = sorted_keys[-1]
                    
                    if name_key and name_key != "name":
                        sn["name"] = sn.pop(name_key)
                    if summary_key and summary_key != "summary":
                        sn["summary"] = sn.pop(summary_key)

    elif phase_number == 3:
        codes_key = None
        for k, v in lists.items():
            if len(v) > 0 and isinstance(v[0], dict):
                item = v[0]
                has_extracts = any(x in item for x in ["extracts", "quotes", "examples", "citations"])
                if has_extracts or "code" in k.lower():
                    codes_key = k
                    break
        if codes_key and codes_key != "codes":
            data["codes"] = data.pop(codes_key)
            
        # Hardened key alignment for codes inside Phase 3
        if "codes" in data and isinstance(data["codes"], list):
            for c in data["codes"]:
                if isinstance(c, dict):
                    # name
                    name_key = None
                    for k in c.keys():
                        if k.lower() in ["name", "code", "code_name", "label", "title"]:
                            name_key = k
                            break
                    if name_key and name_key != "name":
                        c["name"] = c.pop(name_key)
                        
                    # definition
                    def_key = None
                    for k in c.keys():
                        if any(x in k.lower() for x in ["definition", "description", "meaning", "def"]):
                            def_key = k
                            break
                    if def_key and def_key != "definition":
                        c["definition"] = c.pop(def_key)
                        
                    # extracts array
                    exts_key = None
                    for k in c.keys():
                        if any(x in k.lower() for x in ["extracts", "quotes", "examples", "citations", "passages"]):
                            exts_key = k
                            break
                    if exts_key and exts_key != "extracts":
                        c["extracts"] = c.pop(exts_key)
                        
                    # individual extracts
                    if isinstance(c.get("extracts"), list):
                        for ext in c["extracts"]:
                            if isinstance(ext, dict):
                                # text
                                txt_key = None
                                for ek in ext.keys():
                                    if ek.lower() in ["text", "quote", "extract", "content", "passage"]:
                                        txt_key = ek
                                        break
                                if txt_key and txt_key != "text":
                                    ext["text"] = ext.pop(txt_key)
                                    
                                # source name
                                src_key = None
                                for ek in ext.keys():
                                    if any(x in ek.lower() for x in ["source", "file", "document", "participant"]):
                                        src_key = ek
                                        break
                                if src_key and src_key != "source_name":
                                    ext["source_name"] = ext.pop(src_key)

    elif phase_number in (4, 5, 6):
        themes_key = None
        expected_key = "candidate_themes" if phase_number == 4 else "refined_themes" if phase_number == 5 else "final_themes"
        
        for k, v in lists.items():
            if len(v) > 0 and isinstance(v[0], dict):
                item = v[0]
                is_theme = any(x in item for x in ["name", "theme", "theme_name", "title"])
                if is_theme or "theme" in k.lower() or "topic" in k.lower() or "category" in k.lower() or "concept" in k.lower():
                    themes_key = k
                    break
        if themes_key and themes_key != expected_key:
            data[expected_key] = data.pop(themes_key)
            
        # Hardened key alignment for themes inside Phase 4/5/6
        if expected_key in data and isinstance(data[expected_key], list):
            for t in data[expected_key]:
                if isinstance(t, dict):
                    # name
                    name_key = None
                    for k in t.keys():
                        if k.lower() in ["name", "theme", "theme_name", "title"]:
                            name_key = k
                            break
                    if name_key and name_key != "name":
                        t["name"] = t.pop(name_key)
                        
                    # definition
                    def_key = None
                    for k in t.keys():
                        if any(x in k.lower() for x in ["definition", "description", "def"]):
                            def_key = k
                            break
                    if def_key and def_key != "definition":
                        t["definition"] = t.pop(def_key)
                        
                    # code_names
                    codes_key = None
                    for k in t.keys():
                        if any(x in k.lower() for x in ["codes", "code_names", "associated_codes"]):
                            codes_key = k
                            break
                    if codes_key and codes_key != "code_names":
                        t["code_names"] = t.pop(codes_key)
                        
                    # parent_name
                    parent_key = None
                    for k in t.keys():
                        if k.lower() in ["parent", "parent_name", "parent_theme"]:
                            parent_key = k
                            break
                    if parent_key and parent_key != "parent_name":
                        t["parent_name"] = t.pop(parent_key)
                        
    return data
