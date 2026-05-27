import os
import json
from typing import List, Dict, Any

REFERENCES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "references")


def load_reference(filename: str) -> str:
    path = os.path.join(REFERENCES_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def build_system_prompt(phase_number: int) -> str:
    """Build the system prompt for a given phase by injecting reference materials."""

    base_prompt = """You are an expert qualitative research methodologist specializing in thematic analysis following Braun and Clarke (2006).
You are guiding a researcher through a rigorous six-phase thematic analysis.
Your responses should be methodologically sound, academically rigorous, and practically actionable.
Always reference the Braun & Clarke framework explicitly where relevant.

CRITICAL DIRECTIVE ON DATA FIDELITY:
- You MUST NOT hallucinate, fabricate, or paraphrase information as though it is part of the data. 
- You MUST strictly use the exact raw data provided by the user in the context. 
- When generating codes, themes, or notes, base them ONLY on the uploaded sources.
- When extracting quotes, use EXACT, verbatim quotes from the provided text. Do not invent facsimiles or hypothetical examples.

CRITICAL DIRECTIVE ON STATE MANAGEMENT:
When you are asked to return a JSON block containing your analysis (like source_notes, initial_ideas, codes, themes), you are directly updating the application's database.
The JSON you return will COMPLETELY OVERWRITE the existing state for that phase.
Therefore, you MUST include ALL previously generated items that you want to keep, ALONG WITH any new items or updates you have just made. Do not drop existing data unless the user explicitly asks you to delete it!

CRITICAL DIRECTIVE ON JSON FORMATTING:
- You MUST output your analysis as a single, valid, parsable JSON block wrapped in a ```json and ``` code block.
- Place this JSON block at the very end of your response.
- Do not add any text, trailing commas, or markdown comments inside the JSON block.
- You MUST structure your JSON output exactly according to the active phase's schema:
  - Phase 1 (Upfront Decisions):
    {
      "scope": "rich_description" or "detailed_aspect",
      "coding_approach": "inductive" or "theoretical",
      "theme_level": "semantic" or "latent",
      "epistemology": "realist" or "contextualist" or "constructionist",
      "method_statement": "Your one-paragraph methodology description."
    }
  - Phase 2 (Familiarisation):
    {
      "source_notes": [
        { "name": "Exact Name of Source File 1", "summary": "Detailed paragraph of observations." }
      ],
      "initial_ideas": [
        "First initial hunch or starting pattern",
        "Second initial hunch or starting pattern"
      ]
    }
  - Phase 3 (Coding):
    {
      "codes": [
        {
          "name": "Code Label",
          "definition": "Clear boundary definition.",
          "extracts": [
            { "source_name": "Source File Name", "text": "Exact verbatim quote...", "context": "Surrounding sentence context..." }
          ]
        }
      ],
      "coding_notes": "Observations about the coding process."
    }
  - Phase 4 (Theme Search):
    {
      "candidate_themes": [
        { "name": "Theme Name", "definition": "Description of theme", "type": "overarching" or "sub", "parent_name": "Name of parent if sub-theme", "code_names": ["Code Label 1", "Code Label 2"] }
      ],
      "map_description": "Narrative explanation of the map structure.",
      "discarded_codes": ["Code Labels not fitting themes"]
    }
  - Phase 5 (Theme Review):
    {
      "refined_themes": [
        { "name": "Theme Name", "definition": "Refined theme description", "type": "overarching" or "sub", "parent_name": "Parent theme if sub", "code_names": ["Code Label 1"] }
      ],
      "merged_themes": ["Merged theme names"],
      "split_themes": ["Divided theme names"],
      "discarded_themes": ["Discarded theme names"],
      "review_notes": "Detailed Patton homogeneity/heterogeneity review notes."
    }
  - Phase 6 (Defining Themes):
    {
      "final_themes": [
        { "name": "Theme Name", "definition": "Final definition", "type": "overarching" or "sub", "parent_name": "Parent if sub", "sub_themes": ["Sub Theme Name 1"] }
      ],
      "synopsis": "The overall thematic narrative story synopsis.",
      "naming_notes": "Rationale for the punchy named themes chosen."
    }
  - Phase 7 (Report):
    {
      "report_text": "Complete manuscript write-up with Introduction, Method, Findings, and Discussion.",
      "extracts_for_report": [
        { "theme_name": "Theme Name", "extract_text": "Exact quote used...", "commentary": "Rigorous analytic commentary..." }
      ]
    }
"""

    phase_refs = {
        1: ["upfront-decisions.md"],
        2: ["upfront-decisions.md"],
        3: ["coding-guide.md"],
        4: ["theme-development.md", "thematic-map.md"],
        5: ["theme-development.md", "quality-checklist.md"],
        6: ["theme-development.md", "thematic-map.md"],
        7: ["quality-checklist.md", "pitfalls.md"],
    }

    refs = phase_refs.get(phase_number, [])
    ref_texts = [load_reference(r) for r in refs]

    if ref_texts:
        base_prompt += "\n\n## Reference Materials for This Phase\n\n"
        for i, text in enumerate(ref_texts):
            if text:
                base_prompt += f"\n### {refs[i]}\n\n{text}\n\n"

    return base_prompt


def build_phase_user_prompt(phase_number: int, project_context: Dict[str, Any]) -> str:
    """Build the initial user prompt for a given phase."""

    rq = project_context.get("research_question", "(not yet defined)")
    sources = project_context.get("sources", [])
    system_outputs = project_context.get("system_outputs", [])
    decisions = project_context.get("analytic_decisions", {})
    current_phase = project_context.get("current_phase", 0)
    prior_structured = project_context.get("prior_structured_data", {})
    current_structured = project_context.get("current_structured_data", {})

    system_summaries = []
    for s in system_outputs:
        system_summaries.append(f"### File: {s.get('name')}\n{s.get('content', '')}")
    system_text = "\n\n".join(system_summaries) if system_summaries else "No system phase files generated yet."

    system_context = ""
    if system_summaries:
        system_context = f"\n\n=========================================\nGENERATED SYSTEM ANALYSIS FILES (AI MEMORY):\n\n{system_text}\n=========================================\n"

    source_summaries = []
    for s in sources:
        content = s.get("content", "")
        source_summaries.append(f"### Source Name: {s.get('name', 'Unnamed')} ({s.get('source_type', 'unknown')})\n{content}\n")

    source_text = "\n\n".join(source_summaries) if source_summaries else "No sources uploaded yet."
    
    current_state_text = f"\n\nCURRENTLY SAVED STATE FOR THIS PHASE:\n{json.dumps(current_structured, indent=2)}\n\n(Remember: Your JSON output will replace this entirely. You MUST include this existing data alongside any new additions!)" if current_structured else ""

    phase_prompts = {
        0: f"""We are beginning a new thematic analysis project.

Sources loaded into the project:
{source_text}

Research question: {rq}

Please acknowledge the files the user has connected, and then help refine the research question if needed (or guide them to create one if it is not yet defined). It should be broad enough to allow patterned meaning to surface, but narrow enough to discipline what is included and excluded.

Return your response as:
1. A brief welcoming acknowledgment of the connected folder and its files.
2. A brief evaluation of the research question (or guidance on how to create one).
3. A refined version (if changes are needed).
4. Confirmation that we can proceed to Phase 1""",

        1: f"""Phase 1: Interview and planning.

Research question: {rq}

Sources in the data corpus:
{source_text}

The four upfront analytic decisions need to be settled:
1. Rich description of the whole data set, or detailed account of one aspect?
2. Inductive (bottom-up) or theoretical/deductive (top-down) coding?
3. Semantic themes (surface meaning) or latent themes (underlying ideas)?
4. Epistemology: essentialist/realist, contextualist, or constructionist?

Please walk the researcher through each decision. 
CRITICAL: You MUST proactively suggest the best approach for each of the four decisions based heavily on the user's research question and the types of sources they have uploaded. Do not just ask them to choose—give them a well-reasoned recommendation first!

When all four are settled, return a JSON block with the decisions and a one-paragraph method statement.""" + current_state_text,

        2: f"""Phase 2: Familiarising yourself with the data.

Research question: {rq}
Analytic decisions: {decisions}

Sources:
{source_text}

Please read through all sources and produce:
1. A paragraph per source summarising what struck you (patterns, oddities, contradictions)
2. A running list of initial ideas / hunches / possible codes across the data set

These are not yet codes — they are starting ideas for Phase 3.

Return as structured JSON with 'source_notes' (array of {{name, summary}}) and 'initial_ideas' (array of strings).""" + current_state_text,

        3: f"""Phase 3: Generating initial codes.

Research question: {rq}

Familiarisation outputs from Phase 2:
{json.dumps(prior_structured, indent=2) if prior_structured else 'No familiarisation notes have been saved yet.'}

Sources to code:
{source_text}

Work systematically through each source. Code for as many potential patterns as possible.
Code extracts inclusively — keep surrounding context.
A single extract can have multiple codes or none.
Retain contradictory accounts.

For each source, produce a table of extracts with codes applied.
Then produce a consolidated code list with every code and the extracts under it.

Return structured JSON with:
- 'codes': array of {{'name', 'definition', 'extracts': [{{'source_name', 'text', 'context'}}]}}
- 'coding_notes': string with any observations about the coding process""" + current_state_text,

        4: f"""Phase 4: Searching for themes.

Research question: {rq}

Prior coding data:
{json.dumps(prior_structured, indent=2)}

Sort the codes from Phase 3 into potential themes.
A theme captures something important about the data in relation to the research question.
Not all codes need to fit into a theme. You can have a 'miscellaneous' theme.

Please propose an initial set of themes, grouping the codes underneath them.
Discuss this with the researcher and refine the grouping.

Return structured JSON with:
- 'candidate_themes': array of {{'name', 'definition', 'type': 'overarching|sub', 'parent_name', 'code_names': []}}
- 'map_description': string describing the thematic structure
- 'discarded_codes': array of code names that did not fit""" + current_state_text,

        5: f"""Phase 5: Reviewing themes.

Research question: {rq}

Candidate themes from Phase 4:
{json.dumps(prior_structured.get('candidate_themes', []), indent=2) if prior_structured else 'No candidate themes yet.'}

Apply Patton's dual criterion:
- Internal homogeneity: do extracts within each theme cohere?
- External heterogeneity: are themes clearly distinct?

Review Level 1: Check each theme against its coded extracts.
Review Level 2: Check the map against the whole data set.

Return structured JSON with:
- 'refined_themes': array of reviewed themes
- 'merged_themes': array of theme names that were combined
- 'split_themes': array of themes that were divided
- 'discarded_themes': array of themes that did not survive
- 'review_notes': string summary of review decisions""" + current_state_text,

        6: f"""Phase 6: Defining and naming themes.

Research question: {rq}

Refined themes from Phase 5:
{json.dumps(prior_structured.get('refined_themes', []), indent=2) if prior_structured else 'No refined themes yet.'}

For each theme:
1. Identify the essence (what is it really about?)
2. Identify sub-themes (if any)
3. Check against other themes for overlap
4. Give a concise, punchy final name (3-7 words)

Write a one-paragraph synopsis using only theme names and definitions. If it does not tell a coherent story, the themes need more work.

Return structured JSON with:
- 'final_themes': array of {{'name', 'definition', 'type': 'overarching|sub', 'parent_name', 'sub_themes': []}}
- 'synopsis': string — the overall story paragraph
- 'naming_notes': string — rationale for names chosen""" + current_state_text,

        7: f"""Phase 7: Producing the report.

Research question: {rq}
Analytic decisions: {decisions}

Final themes:
{json.dumps(prior_structured.get('final_themes', []), indent=2) if prior_structured else 'No final themes yet.'}

Produce a manuscript-style write-up with:
1. Introduction — research question, rationale, brief note on analytic approach and the four decisions
2. Method — data corpus, analytic procedure describing the six phases (citing Braun & Clarke 2006)
3. Findings — overview paragraph, one section per theme with definition, sub-themes, 2-4 illustrative extracts per theme with analytic commentary that goes BEYOND paraphrase
4. Discussion (brief) — overall story, implications, limitations

Use third person, hedged evidenced claims, active voice when describing analyst actions.
Do not use passive constructions like 'themes emerged'.

Return the full report text in a 'report_text' field.
Also provide 'extracts_for_report': array of {{'theme_name', 'extract_text', 'commentary'}} for key illustrative quotes.""" + current_state_text,
    }

    base_user_prompt = phase_prompts.get(phase_number, "Continue the thematic analysis.")
    if system_context:
        base_user_prompt = f"{system_context}\n\n{base_user_prompt}"
    return base_user_prompt
