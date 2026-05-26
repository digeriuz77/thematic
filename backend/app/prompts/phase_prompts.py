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
    decisions = project_context.get("analytic_decisions", {})
    current_phase = project_context.get("current_phase", 0)
    prior_structured = project_context.get("prior_structured_data", {})

    source_summaries = []
    for s in sources:
        preview = s.get("content", "")[:500]
        source_summaries.append(f"- {s.get('name', 'Unnamed')} ({s.get('source_type', 'unknown')}): {preview}...")

    source_text = "\n".join(source_summaries) if source_summaries else "No sources uploaded yet."

    phase_prompts = {
        0: f"""We are beginning a new thematic analysis project.

Research question: {rq}

Please help refine the research question if needed. It should be broad enough to allow patterned meaning to surface, but narrow enough to discipline what is included and excluded.

Return your response as:
1. A brief evaluation of the research question
2. A refined version (if changes are needed)
3. Confirmation that we can proceed to Phase 1""",

        1: f"""Phase 1: Interview and planning.

Research question: {rq}

Sources in the data corpus:
{source_text}

The four upfront analytic decisions need to be settled:
1. Rich description of the whole data set, or detailed account of one aspect?
2. Inductive (bottom-up) or theoretical/deductive (top-down) coding?
3. Semantic themes (surface meaning) or latent themes (underlying ideas)?
4. Epistemology: essentialist/realist, contextualist, or constructionist?

Please walk the researcher through each decision with brief explanations and ask them to choose.

When all four are settled, return a JSON block with the decisions and a one-paragraph method statement.""",

        2: f"""Phase 2: Familiarising yourself with the data.

Research question: {rq}
Analytic decisions: {decisions}

Sources:
{source_text}

Please read through all sources and produce:
1. A paragraph per source summarising what struck you (patterns, oddities, contradictions)
2. A running list of initial ideas / hunches / possible codes across the data set

These are not yet codes — they are starting ideas for Phase 3.

Return as structured JSON with 'source_notes' (array of {name, summary}) and 'initial_ideas' (array of strings).""",

        3: f"""Phase 3: Generating initial codes.

Research question: {rq}

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
- 'coding_notes': string with any observations about the coding process""",

        4: f"""Phase 4: Searching for themes.

Research question: {rq}

Previous codes:
{json.dumps(prior_structured.get('codes', []), indent=2) if prior_structured else 'No codes yet.'}

Sort the codes into candidate themes. Some codes become themes, some sub-themes, some are discarded.
Identify relationships between codes and themes.
Produce an initial thematic map showing candidate themes and how codes feed into them.

Return structured JSON with:
- 'candidate_themes': array of {{'name', 'definition', 'type': 'overarching|sub', 'parent_name', 'code_names': []}}
- 'map_description': string describing the thematic structure
- 'discarded_codes': array of code names that did not fit""",

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
- 'review_notes': string summary of review decisions""",

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
- 'naming_notes': string — rationale for names chosen""",

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
Also provide 'extracts_for_report': array of {{'theme_name', 'extract_text', 'commentary'}} for key illustrative quotes.""",
    }

    return phase_prompts.get(phase_number, "Continue the thematic analysis.")
