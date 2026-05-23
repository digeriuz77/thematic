import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON, Table
from sqlalchemy.orm import relationship
from backend.app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# Association tables
extract_codes = Table(
    "extract_codes",
    Base.metadata,
    Column("extract_id", String(36), ForeignKey("extracts.id"), primary_key=True),
    Column("code_id", String(36), ForeignKey("codes.id"), primary_key=True),
)

theme_codes = Table(
    "theme_codes",
    Base.metadata,
    Column("theme_id", String(36), ForeignKey("themes.id"), primary_key=True),
    Column("code_id", String(36), ForeignKey("codes.id"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    research_question = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Four upfront analytic decisions (stored as JSON)
    analytic_decisions = Column(JSON, nullable=True)

    # Current phase: 0=setup, 1=interview, 2=familiarisation, ..., 7=report
    current_phase = Column(Integer, default=0)
    phase_status = Column(String(20), default="in_progress")  # in_progress, reviewing, completed

    sources = relationship("Source", back_populates="project", cascade="all, delete-orphan")
    phase_states = relationship("PhaseState", back_populates="project", cascade="all, delete-orphan")
    codes = relationship("Code", back_populates="project", cascade="all, delete-orphan")
    themes = relationship("Theme", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), default="interview")  # interview, journal, survey, other
    content = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="sources")
    extracts = relationship("Extract", back_populates="source", cascade="all, delete-orphan")


class PhaseState(Base):
    __tablename__ = "phase_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    phase_number = Column(Integer, nullable=False)
    ai_transcript = Column(Text, nullable=True)  # JSON array of {role, content} messages
    structured_data = Column(JSON, nullable=True)  # phase-specific structured output
    user_approved = Column(String(20), default="pending")  # pending, approved, revised
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="phase_states")


class Extract(Base):
    __tablename__ = "extracts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    text = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # surrounding text for context
    start_pos = Column(Integer, nullable=True)
    end_pos = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="extracts")
    codes = relationship("Code", secondary="extract_codes", back_populates="extracts")


class Code(Base):
    __tablename__ = "codes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    definition = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="codes")
    extracts = relationship("Extract", secondary="extract_codes", back_populates="codes")
    themes = relationship("Theme", secondary="theme_codes", back_populates="codes")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    definition = Column(Text, nullable=True)
    theme_type = Column(String(20), default="overarching")  # overarching, sub
    parent_id = Column(String(36), ForeignKey("themes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="themes")
    codes = relationship("Code", secondary="theme_codes", back_populates="themes")
    parent = relationship("Theme", remote_side=[id], backref="sub_themes")


class ThematicMap(Base):
    __tablename__ = "thematic_maps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    phase_label = Column(String(20), nullable=False)  # initial, refined, final
    image_path = Column(String(500), nullable=False)
    caption = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    format = Column(String(10), nullable=False)  # pdf, docx
    file_path = Column(String(500), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="reports")
