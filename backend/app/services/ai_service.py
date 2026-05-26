import json
import re
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

    def _get_project_context(self, project: models.Project) -> Dict[str, Any]:
        sources = [
            {"id": s.id, "name": s.name, "source_type": s.source_type, "content": s.content}
            for s in project.sources
        ]

        prior_structured = {}
        if project.current_phase > 0:
            prev_state = (
                self.db.query(models.PhaseState)
                .filter(models.PhaseState.project_id == project.id)
                .filter(models.PhaseState.phase_number == project.current_phase - 1)
                .first()
            )
            if prev_state and prev_state.structured_data:
                prior_structured = prev_state.structured_data

        return {
            "research_question": project.research_question,
            "analytic_decisions": project.analytic_decisions or {},
            "sources": sources,
            "current_phase": project.current_phase,
            "prior_structured_data": prior_structured,
        }

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON block from assistant response."""
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None

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
            context = self._get_project_context(project)
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

        response = requests.post(FIREWORKS_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        response_data = response.json()
        response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        structured_data = self._extract_json(response_text)

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

        self.db.commit()

        return response_text, structured_data