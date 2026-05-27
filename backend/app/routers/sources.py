import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app import models, schemas
from backend.app.config import get_settings

router = APIRouter()
settings = get_settings()


def extract_text_from_file(file_path: str, filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    if ext in ('txt', 'md', 'markdown'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    elif ext == 'docx':
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif ext == 'pdf':
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])

    elif ext in ('csv', 'xlsx', 'xls'):
        import pandas as pd
        if ext == 'csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        # Try to find a text column, otherwise dump all
        text_cols = [c for c in df.columns if any(k in c.lower() for k in ['text', 'content', 'transcript', 'response', 'answer'])]
        if text_cols:
            return "\n\n---\n\n".join(df[text_cols[0]].astype(str).tolist())
        return df.to_string()

    else:
        raise ValueError(f"Unsupported file type: .{ext}")


@router.post("/upload", response_model=schemas.SourceResponse)
async def upload_source(
    project_id: str = Form(...),
    name: str = Form(...),
    source_type: str = Form("interview"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save file to uploads directory
    safe_name = os.path.basename(file.filename or "upload")
    dest_path = os.path.join(settings.uploads_dir, f"{project_id}_{safe_name}")
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        content = extract_text_from_file(dest_path, safe_name)
    except Exception as e:
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail=f"Could not extract text: {str(e)}")

    db_source = models.Source(
        project_id=project_id,
        name=name or safe_name,
        source_type=source_type,
        content=content,
        file_path=dest_path,
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


@router.post("/paste", response_model=schemas.SourceResponse)
def paste_source(source: schemas.SourceCreate, project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_source = models.Source(
        project_id=project_id,
        name=source.name,
        source_type=source.source_type,
        content=source.content,
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


@router.get("/project/{project_id}", response_model=List[schemas.SourceResponse])
def list_sources(project_id: str, db: Session = Depends(get_db)):
    return db.query(models.Source).filter(models.Source.project_id == project_id).all()


@router.delete("/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.file_path and os.path.exists(source.file_path):
        os.remove(source.file_path)
    db.delete(source)
    db.commit()
    return {"detail": "Source deleted"}
