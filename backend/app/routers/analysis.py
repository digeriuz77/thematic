import json
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app import models, schemas
from backend.app.services.ai_service import AIService
from backend.app.services.report_service import ReportService
from backend.app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/phase-state/{project_id}/{phase_number}", response_model=Optional[schemas.PhaseStateResponse])
def get_phase_state(project_id: str, phase_number: int, db: Session = Depends(get_db)):
    state = (
        db.query(models.PhaseState)
        .filter(models.PhaseState.project_id == project_id)
        .filter(models.PhaseState.phase_number == phase_number)
        .first()
    )
    return state


@router.put("/phase-state/{project_id}/{phase_number}")
def update_phase_state(project_id: str, phase_number: int, data: dict, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    state = (
        db.query(models.PhaseState)
        .filter(models.PhaseState.project_id == project_id)
        .filter(models.PhaseState.phase_number == phase_number)
        .first()
    )
    if not state:
        state = models.PhaseState(
            project_id=project_id,
            phase_number=phase_number,
            structured_data=data
        )
        db.add(state)
    else:
        state.structured_data = data
        state.updated_at = __import__("datetime").datetime.utcnow()
        
    db.commit()
    db.refresh(state)

    # Sync upfront decisions directly to the project model if it's Phase 1
    if phase_number == 1 and data:
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
            val = find_val(data, key)
            if val:
                decisions[key] = val
        project.analytic_decisions = decisions
        db.commit()

    # Save to physical JSON/MD files and synchronize relational database tables!
    ai_service = AIService(db)
    try:
        ai_service.save_phase_data_to_file(project, phase_number, data)
        ai_service.sync_structured_data_to_db(project, phase_number, data)
    except Exception as e:
        print(f"Error saving/syncing phase data during manual PUT: {e}")

    return {"status": "success", "structured_data": state.structured_data}


@router.post("/chat", response_model=schemas.PhaseChatResponse)
def phase_chat(request: schemas.PhaseChatRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ai_service = AIService(db)
    response_text, structured_data = ai_service.run_phase_chat(
        project=project,
        phase_number=request.phase_number,
        messages=[m.model_dump() for m in request.messages],
    )

    return schemas.PhaseChatResponse(
        response=response_text,
        structured_data=structured_data,
    )


@router.get("/validate-phase/{project_id}/{phase_number}")
def validate_phase(project_id: str, phase_number: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ai_service = AIService(db)
    valid, errors = ai_service.validate_phase_data(project, phase_number)
    return {"valid": valid, "errors": errors}


@router.post("/advance-phase/{project_id}")
def advance_phase(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.current_phase >= 7:
        raise HTTPException(status_code=400, detail="Already at final phase")

    project.current_phase += 1
    project.phase_status = "in_progress"
    db.commit()
    db.refresh(project)
    return {"current_phase": project.current_phase, "phase_status": project.phase_status}


@router.post("/previous-phase/{project_id}")
def previous_phase(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.current_phase <= 0:
        raise HTTPException(status_code=400, detail="Already at first phase")

    project.current_phase -= 1
    project.phase_status = "in_progress"
    
    # Optionally, we could clear the PhaseState for the phase we are leaving,
    # but keeping it allows the user to restore their progress if they advance again.
    
    db.commit()
    db.refresh(project)
    return {"current_phase": project.current_phase, "phase_status": project.phase_status}


@router.post("/reset-project/{project_id}")
def reset_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Wipe all phase states to start completely fresh
    db.query(models.PhaseState).filter(models.PhaseState.project_id == project_id).delete()

    # Wipe all system phase output sources and delete physical files from disk
    sys_sources = (
        db.query(models.Source)
        .filter(models.Source.project_id == project_id)
        .filter(models.Source.source_type == "phase_output")
        .all()
    )
    
    for s in sys_sources:
        if s.file_path and os.path.exists(s.file_path):
            try:
                os.remove(s.file_path)
                # also try to remove the JSON version if it exists
                json_path = s.file_path.replace(".md", ".json")
                if os.path.exists(json_path):
                    os.remove(json_path)
            except Exception:
                pass
        db.delete(s)

    project.current_phase = 0
    project.phase_status = "in_progress"
    project.analytic_decisions = {}
    
    db.commit()
    db.refresh(project)
    return {"current_phase": project.current_phase, "phase_status": project.phase_status}


@router.post("/generate-report/{project_id}")
def generate_report(project_id: str, format: str = "pdf", db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.current_phase < 7:
        raise HTTPException(status_code=400, detail="Analysis not complete")

    report_service = ReportService(db)
    file_path = report_service.generate_report(project, format=format)

    db_report = models.Report(
        project_id=project_id,
        format=format,
        file_path=file_path,
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    return schemas.ReportResponse.model_validate(db_report)


@router.get("/reports/{project_id}", response_model=list[schemas.ReportResponse])
def list_reports(project_id: str, db: Session = Depends(get_db)):
    return db.query(models.Report).filter(models.Report.project_id == project_id).all()


@router.get("/download/{filename}")
def download_report(filename: str):
    file_path = os.path.join(settings.reports_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)
