"""
Database Models
================
User        - stores registered users
Analysis    - stores every resume analysis with ATS score
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(100), nullable=False)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # One user can have many analyses
    analyses = relationship("Analysis", back_populates="user",
                            cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Input
    job_description = Column(Text, nullable=False)
    resume_text     = Column(Text, nullable=True)

    # AI Analysis results
    role             = Column(String(200))
    gaps             = Column(JSON)   # list of {skill, reason}
    new_projects     = Column(JSON)   # list of {title, why, tech, steps}
    upgrade_projects = Column(JSON)   # list of {title, why, tech, steps}

    # ATS Score results
    ats_score        = Column(Float)          # 0 to 100
    ats_grade        = Column(String(2))      # A, B, C, D, F
    matched_keywords = Column(JSON)           # list of matched keywords
    missing_keywords = Column(JSON)           # list of missing keywords

    # Relationship back to user
    user = relationship("User", back_populates="analyses")
