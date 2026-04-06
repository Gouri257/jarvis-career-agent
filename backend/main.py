"""
JARVIS Career Agent — FastAPI Backend
======================================
Endpoints:
    POST /auth/register         - Create new account
    POST /auth/login            - Login, get JWT token
    GET  /auth/me               - Get current user info
    POST /analyze               - Run full analysis + ATS score
    GET  /history               - Get all analyses for current user
    GET  /analysis/{id}         - Get one specific analysis
    DELETE /analysis/{id}       - Delete one analysis
    GET  /health                - Health check
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from database import get_db, engine
import models, schemas, auth, analyzer

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JARVIS Career Agent API",
    description="AI-powered resume analyzer with ATS scoring",
    version="2.0.0"
)

# Allow requests from your web app and desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@app.get("/health")
def health_check():
    return {"status": "JARVIS is online", "version": "2.0.0"}


# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(models.User).filter(
        models.User.email == user.email
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )

    # Create new user
    new_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=auth.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Find user by email
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token that lasts 7 days
    token = auth.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=7)
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ══════════════════════════════════════════════════════════════
# ANALYZE ROUTE — the main feature
# ══════════════════════════════════════════════════════════════

@app.post("/analyze", response_model=schemas.AnalysisOut)
def run_analysis(
    request: schemas.AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # Step 1: Compute ATS score using TF-IDF + cosine similarity
        ats_result = analyzer.compute_ats_score(
            resume_text=request.resume_text,
            job_description=request.job_description
        )

        # Step 2: Get AI analysis from Groq
        ai_result = analyzer.get_ai_analysis(
            resume_text=request.resume_text,
            job_description=request.job_description,
            groq_api_key=request.groq_api_key
        )

        # Step 3: Save everything to database
        analysis = models.Analysis(
            user_id=current_user.id,
            job_description=request.job_description,
            resume_text=request.resume_text,
            role=ai_result.get("role", "Unknown"),
            ats_score=ats_result["score"],
            ats_grade=ats_result["grade"],
            matched_keywords=ats_result["matched_keywords"],
            missing_keywords=ats_result["missing_keywords"],
            gaps=ai_result.get("gaps", []),
            new_projects=ai_result.get("new_projects", []),
            upgrade_projects=ai_result.get("upgrade_projects", []),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# HISTORY ROUTES
# ══════════════════════════════════════════════════════════════

@app.get("/history", response_model=List[schemas.AnalysisSummary])
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    analyses = db.query(models.Analysis).filter(
        models.Analysis.user_id == current_user.id
    ).order_by(models.Analysis.created_at.desc()).all()
    return analyses


@app.get("/analysis/{analysis_id}", response_model=schemas.AnalysisOut)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    analysis = db.query(models.Analysis).filter(
        models.Analysis.id == analysis_id,
        models.Analysis.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.delete("/analysis/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    analysis = db.query(models.Analysis).filter(
        models.Analysis.id == analysis_id,
        models.Analysis.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    db.delete(analysis)
    db.commit()
    return {"message": "Analysis deleted successfully"}
