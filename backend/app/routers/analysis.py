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
