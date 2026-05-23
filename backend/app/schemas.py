from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SourceCreate(BaseModel):
    name: str
    source_type: str = "interview"
    content: str


class SourceResponse(BaseModel):
    id: str
    project_id: str
    name: str
    source_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    research_question: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    research_question: Optional[str] = None
    analytic_decisions: Optional[Dict[str, Any]] = None
    current_phase: Optional[int] = None
    phase_status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    research_question: Optional[str]
    created_at: datetime
    updated_at: datetime
    analytic_decisions: Optional[Dict[str, Any]]
    current_phase: int
    phase_status: str

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    sources: List[SourceResponse] = []


class PhaseStateResponse(BaseModel):
    id: str
    project_id: str
    phase_number: int
    ai_transcript: Optional[str]
    structured_data: Optional[Dict[str, Any]]
    user_approved: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class PhaseChatRequest(BaseModel):
    messages: List[ChatMessage]
    project_id: str
    phase_number: int


class PhaseChatResponse(BaseModel):
    response: str
    structured_data: Optional[Dict[str, Any]] = None


class CodeResponse(BaseModel):
    id: str
    project_id: str
    name: str
    definition: Optional[str]
    color: str
    created_at: datetime

    class Config:
        from_attributes = True


class ThemeResponse(BaseModel):
    id: str
    project_id: str
    name: str
    definition: Optional[str]
    theme_type: str
    parent_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    id: str
    project_id: str
    format: str
    file_path: str
    generated_at: datetime

    class Config:
        from_attributes = True
