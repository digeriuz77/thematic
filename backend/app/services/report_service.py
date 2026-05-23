import os
import json
import base64
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from backend.app.config import get_settings
from backend.app import models

settings = get_settings()


@dataclass
class ReportTheme:
    id: str
    name: str
    definition: str = ""
    theme_type: str = "overarching"
    parent_id: str | None = None
    parent_name: str | None = None


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

    def _phase_structured_data(self, project_id: str, phase_number: int) -> Dict[str, Any]:
        phase_state = (
            self.db.query(models.PhaseState)
            .filter(models.PhaseState.project_id == project_id)
            .filter(models.PhaseState.phase_number == phase_number)
            .first()
        )
        return phase_state.structured_data if phase_state and phase_state.structured_data else {}

    def _themes_from_structured_data(self, data: Dict[str, Any]) -> List[ReportTheme]:
        raw_themes = (
            data.get("final_themes")
            or data.get("refined_themes")
            or data.get("candidate_themes")
            or []
        )

        themes: List[ReportTheme] = []

        for index, raw in enumerate(raw_themes):
            if isinstance(raw, str):
                raw = {"name": raw}
            if not isinstance(raw, dict) or not raw.get("name"):
                continue

            theme_name = str(raw["name"])
            theme_type = raw.get("theme_type") or raw.get("type") or "overarching"
            parent_name = raw.get("parent_name") or raw.get("parent")
            theme = ReportTheme(
                id=f"theme-{index}",
                name=theme_name,
                definition=str(raw.get("definition") or ""),
                theme_type=theme_type,
                parent_name=parent_name,
            )
            themes.append(theme)

            for sub_index, sub_theme in enumerate(raw.get("sub_themes") or []):
                if isinstance(sub_theme, str):
                    sub_theme = {"name": sub_theme}
                if not isinstance(sub_theme, dict) or not sub_theme.get("name"):
                    continue
                themes.append(
                    ReportTheme(
                        id=f"theme-{index}-sub-{sub_index}",
                        name=str(sub_theme["name"]),
                        definition=str(sub_theme.get("definition") or ""),
                        theme_type="sub",
                        parent_name=theme_name,
                    )
                )

        name_to_id = {theme.name: theme.id for theme in themes}
        for theme in themes:
            if theme.parent_name and not theme.parent_id:
                theme.parent_id = name_to_id.get(theme.parent_name)

        return themes

    def _get_themes(self, project: models.Project) -> List[Any]:
        db_themes = (
            self.db.query(models.Theme)
            .filter(models.Theme.project_id == project.id)
            .all()
        )
        if db_themes:
            return db_themes

        for phase_number in (6, 5, 4):
            themes = self._themes_from_structured_data(
                self._phase_structured_data(project.id, phase_number)
            )
            if themes:
                return themes

        return []

    def _get_project_data(self, project: models.Project) -> Dict[str, Any]:
        """Gather all project data for report generation."""
        themes = self._get_themes(project)

        # Get final map
        final_map = (
            self.db.query(models.ThematicMap)
            .filter(models.ThematicMap.project_id == project.id)
            .filter(models.ThematicMap.phase_label == "final")
            .first()
        )

        # Get phase 7 state for report text
        phase7_state = (
            self.db.query(models.PhaseState)
            .filter(models.PhaseState.project_id == project.id)
            .filter(models.PhaseState.phase_number == 7)
            .first()
        )

        report_text = ""
        extracts_for_report = []
        if phase7_state and phase7_state.structured_data:
            report_text = phase7_state.structured_data.get("report_text", "")
            extracts_for_report = phase7_state.structured_data.get("extracts_for_report", [])

        return {
            "project": project,
            "themes": themes,
            "final_map_path": final_map.image_path if final_map else None,
            "report_text": report_text,
            "extracts_for_report": extracts_for_report,
            "analytic_decisions": project.analytic_decisions or {},
            "research_question": project.research_question or "",
            "source_count": len(project.sources),
        }

    def generate_thematic_map_image(
        self,
        project_id: str,
        themes: List[Any],
        phase_label: str = "final",
    ) -> str:
        """Generate a thematic map PNG using matplotlib, adapted from references/thematic-map.md."""
        # Organize themes
        overarching = [t for t in themes if t.theme_type == "overarching"]
        subs = [t for t in themes if t.theme_type == "sub"]

        fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
        ax.set_xlim(0, 14)
        ax.set_ylim(0, 10)
        ax.axis("off")

        THEME_FACE = "#E8E8E8"
        SUBTHEME_FACE = "#FFFFFF"
        EDGE = "#333333"
        FONT = {"family": "serif", "fontsize": 11}

        def draw_theme(x, y, label, width=3.0, height=1.2):
            ellipse = mpatches.Ellipse(
                (x, y), width, height,
                facecolor=THEME_FACE, edgecolor=EDGE, linewidth=1.5
            )
            ax.add_patch(ellipse)
            ax.text(x, y, label, ha="center", va="center", fontweight="bold", wrap=True, **FONT)
            return (x, y)

        def draw_subtheme(x, y, label, width=2.4, height=0.7):
            rect = mpatches.FancyBboxPatch(
                (x - width / 2, y - height / 2),
                width, height,
                boxstyle="round,pad=0.05",
                facecolor=SUBTHEME_FACE,
                edgecolor=EDGE, linewidth=1.0
            )
            ax.add_patch(rect)
            ax.text(x, y, label, ha="center", va="center", wrap=True, fontsize=9, family="serif")
            return (x, y)

        def connect(x1, y1, x2, y2):
            ax.plot([x1, x2], [y1, y2], color=EDGE, linewidth=0.8, zorder=0)

        # Simple layout: distribute overarching themes across top
        n_over = len(overarching)
        if n_over == 0:
            n_over = 1
            overarching = [None]

        positions = []
        for i, theme in enumerate(overarching):
            x = 2 + (i * (10 / max(n_over - 1, 1))) if n_over > 1 else 7
            y = 8.5
            if theme:
                pos = draw_theme(x, y, theme.name)
                positions.append((theme, pos))
            else:
                positions.append((None, (x, y)))

        # Place sub-themes under their parents
        for theme, (tx, ty) in positions:
            if not theme:
                continue
            theme_subs = [s for s in subs if s.parent_id == theme.id]
            n_subs = len(theme_subs)
            for j, sub in enumerate(theme_subs):
                sx = tx - 1.5 + (j * (3 / max(n_subs - 1, 1))) if n_subs > 1 else tx
                sy = 6.0 - (j % 2) * 0.3  # slight stagger
                draw_subtheme(sx, sy, sub.name)
                connect(tx, ty - 0.6, sx, sy + 0.35)

        plt.tight_layout()

        out_path = os.path.join(settings.maps_dir, f"{project_id}_{phase_label}_map.png")
        plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        # Save to DB
        existing = (
            self.db.query(models.ThematicMap)
            .filter(models.ThematicMap.project_id == project_id)
            .filter(models.ThematicMap.phase_label == phase_label)
            .first()
        )
        if existing:
            existing.image_path = out_path
        else:
            db_map = models.ThematicMap(
                project_id=project_id,
                phase_label=phase_label,
                image_path=out_path,
                caption=f"{phase_label.capitalize()} thematic map",
            )
            self.db.add(db_map)
        self.db.commit()

        return out_path

    def generate_report(self, project: models.Project, format: str = "pdf") -> str:
        """Generate a downloadable report (PDF or DOCX)."""
        data = self._get_project_data(project)

        # Ensure thematic map exists
        existing_map = (
            self.db.query(models.ThematicMap)
            .filter(models.ThematicMap.project_id == project.id)
            .filter(models.ThematicMap.phase_label == "final")
            .first()
        )
        if data["themes"] and (not existing_map or not os.path.exists(existing_map.image_path)):
            self.generate_thematic_map_image(project.id, data["themes"], phase_label="final")
            data = self._get_project_data(project)

        if format == "pdf":
            return self._generate_pdf(data)
        elif format == "docx":
            return self._generate_docx(data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_pdf(self, data: Dict[str, Any]) -> str:
        """Generate PDF via Playwright HTML-to-PDF."""
        from playwright.sync_api import sync_playwright

        project = data["project"]
        out_path = os.path.join(settings.reports_dir, f"{project.id}_report.pdf")

        # Build HTML content
        html_content = self._build_report_html(data)

        # Write temp HTML
        html_path = os.path.join(settings.reports_dir, f"{project.id}_report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Convert to PDF
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file:///{html_path}")
            page.pdf(path=out_path, format="A4", margin={"top": "40px", "bottom": "40px", "left": "40px", "right": "40px"})
            browser.close()

        return out_path

    def _build_report_html(self, data: Dict[str, Any]) -> str:
        """Build a dark-themed HTML report matching analyse.py style."""
        project = data["project"]
        themes = data.get("themes", [])
        report_text = data.get("report_text", "")
        map_path = data.get("final_map_path")

        # Encode map image as base64 for embedding
        map_b64 = ""
        if map_path and os.path.exists(map_path):
            with open(map_path, "rb") as img:
                map_b64 = base64.b64encode(img.read()).decode()

        theme_rows = ""
        for t in themes:
            theme_rows += f"""
            <tr>
                <td><strong>{escape(t.name)}</strong></td>
                <td>{escape(t.definition or "")}</td>
                <td>{escape(t.theme_type)}</td>
            </tr>"""

        report_body = "<p>No report text generated yet.</p>"
        if report_text:
            escaped_report = escape(report_text)
            report_body = "<p>" + escaped_report.replace("\n\n", "</p><p>").replace("\n", "<br/>") + "</p>"

        report_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>{escape(project.title)} - Thematic Analysis Report</title>
<style>
  @page {{ margin: 40px; }}
  body {{ background: #fff; color: #1a1a2e; font-family: 'Segoe UI', sans-serif; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; }}
  h1 {{ color: #6366f1; font-size: 1.8rem; margin-bottom: 4px; }}
  h2 {{ color: #4f46e5; font-size: 1.3rem; margin-top: 32px; margin-bottom: 12px; border-bottom: 1px solid #e0e7ff; padding-bottom: 6px; }}
  h3 {{ color: #4338ca; font-size: 1.1rem; margin-top: 24px; }}
  .meta {{ color: #64748b; font-size: .9rem; margin-bottom: 24px; }}
  .decisions {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 24px; font-size: .9rem; }}
  .decisions strong {{ color: #4f46e5; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th {{ background: #eef2ff; color: #4338ca; padding: 10px 12px; text-align: left; font-size: .8rem; text-transform: uppercase; letter-spacing: .4px; border-bottom: 2px solid #c7d2fe; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-size: .9rem; }}
  .extract {{ background: #f8fafc; border-left: 4px solid #6366f1; padding: 12px 16px; margin: 12px 0; font-style: italic; color: #334155; }}
  .commentary {{ margin: 8px 0 16px 0; color: #475569; }}
  img {{ max-width: 100%; height: auto; margin: 16px 0; }}
  .map-caption {{ text-align: center; font-size: .85rem; color: #64748b; margin-bottom: 24px; }}
</style>
</head><body>
<h1>{escape(project.title)}</h1>
<div class="meta">Thematic Analysis Report | Braun &amp; Clarke (2006) Six-Phase Framework | Generated {datetime.utcnow().strftime('%Y-%m-%d')}</div>

<h2>Research Question</h2>
<p>{escape(data.get('research_question', 'Not specified'))}</p>
<div class="decisions">
<strong>Analytic Decisions:</strong><br/>
<pre>{escape(json.dumps(data.get('analytic_decisions', {}), indent=2))}</pre>
</div>

<h2>Themes</h2>
<table>
<thead><tr><th>Name</th><th>Definition</th><th>Type</th></tr></thead>
<tbody>{theme_rows}</tbody>
</table>

<h2>Thematic Map</h2>
{'<img src="data:image/png;base64,' + map_b64 + '" />' if map_b64 else '<p>No thematic map generated.</p>'}
<div class="map-caption">Figure 1. Final thematic map showing overarching themes and sub-themes.</div>

<h2>Analysis Report</h2>
{report_body}

</body></html>"""

        return report_html

    def _generate_docx(self, data: Dict[str, Any]) -> str:
        """Generate DOCX manuscript."""
        project = data["project"]
        out_path = os.path.join(settings.reports_dir, f"{project.id}_report.docx")

        doc = Document()

        # Title
        title = doc.add_heading(project.title, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Meta
        meta = doc.add_paragraph()
        meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_run = meta.add_run(f"Thematic Analysis Report | Generated {datetime.utcnow().strftime('%Y-%m-%d')}")
        meta_run.font.size = Pt(10)
        meta_run.font.color.rgb = RGBColor(0x64, 0x70, 0x8B)

        doc.add_paragraph()

        # Research question
        doc.add_heading("Research Question", level=1)
        doc.add_paragraph(data.get("research_question", "Not specified"))

        # Analytic decisions
        doc.add_heading("Analytic Decisions", level=1)
        decisions = data.get("analytic_decisions", {})
        for key, value in decisions.items():
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(f"{key}: ").bold = True
            p.add_run(str(value))

        # Themes
        doc.add_heading("Themes", level=1)
        themes = data.get("themes", [])
        for t in themes:
            doc.add_heading(t.name, level=2)
            doc.add_paragraph(t.definition or "")

        # Thematic map
        map_path = data.get("final_map_path")
        if map_path and os.path.exists(map_path):
            doc.add_heading("Thematic Map", level=1)
            doc.add_picture(map_path, width=Inches(6))
            caption = doc.add_paragraph("Figure 1. Final thematic map.")
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Report text
        report_text = data.get("report_text", "")
        if report_text:
            doc.add_heading("Findings", level=1)
            doc.add_paragraph(report_text)

        doc.save(out_path)
        return out_path
