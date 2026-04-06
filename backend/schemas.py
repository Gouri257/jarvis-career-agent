"""
Pydantic Schemas
=================
These define what data comes IN to the API and what goes OUT.
FastAPI uses these to automatically validate requests and format responses.
"""

from pydantic import BaseModel, EmailStr
from typing import List, Optional, Any
from datetime import datetime


# ── Auth Schemas ──────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# ── Analysis Schemas ──────────────────────────────────────────

class AnalysisRequest(BaseModel):
    resume_text: Optional[str] = ""
    job_description: str
    groq_api_key: str


class AnalysisSummary(BaseModel):
    """Short version shown in history list"""
    id: int
    role: str
    ats_score: float
    ats_grade: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisOut(BaseModel):
    """Full analysis with all details"""
    id: int
    role: str
    created_at: datetime

    # ATS Score
    ats_score: float
    ats_grade: str
    matched_keywords: List[str]
    missing_keywords: List[str]

    # AI Analysis
    gaps: List[Any]
    new_projects: List[Any]
    upgrade_projects: List[Any]

    class Config:
        from_attributes = True
