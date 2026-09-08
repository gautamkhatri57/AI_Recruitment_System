import secrets
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Admin,
    InterviewAnswer,
    InterviewQuestion,
    JobPosition,
    Resume,
    ResumeAnalysis,
    User,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

security = HTTPBearer()

admin_sessions = {}


# =========================================================
# REQUEST MODELS
# =========================================================

class PositionRequest(BaseModel):
    title: str
    description: str
    required_skills: str
    education: Optional[str] = None
    experience_required: Optional[str] = None
    responsibilities: Optional[str] = None
    is_active: bool = True


# =========================================================
# ADMIN AUTH
# =========================================================

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    admin_id = admin_sessions.get(token)

    if not admin_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin session",
        )

    admin = (
        db.query(Admin)
        .filter(
            Admin.id == admin_id,
            Admin.is_active == True,
        )
        .first()
    )

    if not admin:
        raise HTTPException(
            status_code=401,
            detail="Admin not found or inactive",
        )

    return admin


# =========================================================
# ADMIN LOGIN
# =========================================================

@router.post("/login")
def admin_login(
    email: str,
    password: str,
    db: Session = Depends(get_db),
):
    admin = (
        db.query(Admin)
        .filter(Admin.email == email)
        .first()
    )

    if not admin:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=403,
            detail="Admin account is inactive",
        )

    try:
        password_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            admin.password_hash.encode("utf-8"),
        )
    except Exception:
        password_valid = False

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = secrets.token_urlsafe(32)

    admin_sessions[token] = admin.id

    return {
        "message": "Login successful",
        "token": token,
        "admin": {
            "id": admin.id,
            "full_name": admin.full_name,
            "email": admin.email,
        },
    }


# =========================================================
# LOGOUT
# =========================================================

@router.post("/logout")
def admin_logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    admin_sessions.pop(token, None)

    return {
        "message": "Logout successful"
    }


# =========================================================
# ADMIN ME
# =========================================================

@router.get("/me")
def admin_me(
    admin: Admin = Depends(get_current_admin),
):
    return {
        "id": admin.id,
        "full_name": admin.full_name,
        "email": admin.email,
    }


# =========================================================
# DASHBOARD
# =========================================================

@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    total_candidates = db.query(User).count()

    total_resumes = db.query(Resume).count()

    total_positions = (
        db.query(JobPosition)
        .filter(JobPosition.is_active == True)
        .count()
    )

    total_analyses = db.query(
        ResumeAnalysis
    ).count()

    return {
        "total_candidates": total_candidates,
        "total_resumes": total_resumes,
        "total_positions": total_positions,
        "total_analyses": total_analyses,
    }


# =========================================================
# GET ALL CANDIDATES
# =========================================================

@router.get("/candidates")
def get_candidates(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    resumes = (
        db.query(Resume)
        .join(User, Resume.user_id == User.id)
        .join(
            JobPosition,
            Resume.job_position_id == JobPosition.id,
        )
        .order_by(Resume.uploaded_at.desc())
        .all()
    )

    result = []

    for resume in resumes:

        user = resume.user
        position = resume.job_position
        analysis = resume.analysis

        resume_score = (
            analysis.score
            if analysis and analysis.score is not None
            else None
        )

        interview_score = (
            analysis.interview_score
            if analysis and analysis.interview_score is not None
            else None
        )

        overall_score = (
            analysis.overall_score
            if analysis and analysis.overall_score is not None
            else None
        )

        recommendation = (
            analysis.final_recommendation
            if analysis
            else None
        )

        result.append(
            {
                "id": user.id,
                "user_id": user.id,
                "resume_id": resume.id,

                "full_name": user.full_name,
                "name": user.full_name,

                "email": user.email,
                "phone": user.phone,

                "position_title": (
                    position.title
                    if position
                    else None
                ),

                "original_filename": (
                    resume.original_filename
                ),

                "resume_score": resume_score,
                "score": resume_score,

                "interview_score": interview_score,

                "overall_score": overall_score,

                "final_recommendation": recommendation,
                "recommendation": recommendation,

                "candidate": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                },

                "position": (
                    {
                        "id": position.id,
                        "title": position.title,
                        "description": position.description,
                        "required_skills": position.required_skills,
                        "education": position.education,
                        "experience_required": position.experience_required,
                        "responsibilities": position.responsibilities,
                    }
                    if position
                    else None
                ),

                "resume": {
                    "id": resume.id,
                    "original_filename": resume.original_filename,
                    "file_path": resume.file_path,
                    "uploaded_at": resume.uploaded_at,
                },

                "analysis": (
                    {
                        "id": analysis.id,
                        "score": analysis.score,
                        "strengths": analysis.strengths,
                        "weaknesses": analysis.weaknesses,
                        "suggestions": analysis.suggestions,
                        "interview_score": analysis.interview_score,
                        "overall_score": analysis.overall_score,
                        "final_recommendation": analysis.final_recommendation,
                    }
                    if analysis
                    else None
                ),
            }
        )

    return result


# =========================================================
# CANDIDATE DETAILS
# =========================================================

@router.get("/candidates/{resume_id}")
def get_candidate_details(
    resume_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    user = resume.user
    position = resume.job_position
    analysis = resume.analysis

    questions = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.resume_id == resume.id
        )
        .order_by(InterviewQuestion.id.asc())
        .all()
    )

    question_data = []

    for question in questions:

        answers = (
            db.query(InterviewAnswer)
            .filter(
                InterviewAnswer.question_id
                == question.id
            )
            .order_by(InterviewAnswer.id.asc())
            .all()
        )

        answer_data = []

        for answer in answers:
            answer_data.append(
                {
                    "id": answer.id,
                    "answer": answer.answer,
                    "evaluation": answer.evaluation,
                    "score": answer.score,
                    "created_at": answer.created_at,
                }
            )

        latest_answer = (
            answer_data[-1]
            if answer_data
            else None
        )

        question_data.append(
            {
                "id": question.id,

                "question": question.question,
                "question_text": question.question,

                "created_at": question.created_at,

                "answer": (
                    latest_answer["answer"]
                    if latest_answer
                    else None
                ),

                "score": (
                    latest_answer["score"]
                    if latest_answer
                    else None
                ),

                "evaluation": (
                    latest_answer["evaluation"]
                    if latest_answer
                    else None
                ),

                "answers": answer_data,
            }
        )

    return {
        "id": user.id,
        "user_id": user.id,
        "resume_id": resume.id,

        "full_name": user.full_name,
        "name": user.full_name,

        "email": user.email,
        "phone": user.phone,

        "position_title": (
            position.title
            if position
            else None
        ),

        "original_filename": (
            resume.original_filename
        ),

        "resume_score": (
            analysis.score
            if analysis
            else None
        ),

        "score": (
            analysis.score
            if analysis
            else None
        ),

        "interview_score": (
            analysis.interview_score
            if analysis
            else None
        ),

        "overall_score": (
            analysis.overall_score
            if analysis
            else None
        ),

        "final_recommendation": (
            analysis.final_recommendation
            if analysis
            else None
        ),

        "recommendation": (
            analysis.final_recommendation
            if analysis
            else None
        ),

        "candidate": {
            "id": user.id,
            "full_name": user.full_name,
            "name": user.full_name,
            "email": user.email,
            "phone": user.phone,
        },

        "position": (
            {
                "id": position.id,
                "title": position.title,
                "description": position.description,
                "required_skills": position.required_skills,
                "education": position.education,
                "experience_required": position.experience_required,
                "responsibilities": position.responsibilities,
            }
            if position
            else None
        ),

        "resume": {
            "id": resume.id,
            "original_filename": resume.original_filename,
            "file_path": resume.file_path,
            "uploaded_at": resume.uploaded_at,
        },

        "analysis": (
            {
                "id": analysis.id,
                "score": analysis.score,
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses,
                "suggestions": analysis.suggestions,
                "interview_score": analysis.interview_score,
                "overall_score": analysis.overall_score,
                "final_recommendation": analysis.final_recommendation,
            }
            if analysis
            else None
        ),

        "interview": {
            "questions": question_data
        },

        "interview_questions": question_data,
        "questions": question_data,
    }


# =========================================================
# GET ALL POSITIONS
# =========================================================

@router.get("/positions")
def get_positions(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    positions = (
        db.query(JobPosition)
        .order_by(JobPosition.id.desc())
        .all()
    )

    result = []

    for position in positions:

        result.append(
            {
                "id": position.id,
                "title": position.title,
                "description": position.description,
                "required_skills": position.required_skills,
                "education": position.education,
                "experience_required": position.experience_required,
                "responsibilities": position.responsibilities,
                "is_active": position.is_active,
                "created_at": position.created_at,
            }
        )

    return result


# =========================================================
# CREATE POSITION
# =========================================================

@router.post("/positions")
def create_position(
    payload: PositionRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    title = payload.title.strip()
    description = payload.description.strip()
    required_skills = payload.required_skills.strip()

    education = (
        payload.education.strip()
        if payload.education
        else ""
    )

    experience_required = (
        payload.experience_required.strip()
        if payload.experience_required
        else ""
    )

    responsibilities = (
        payload.responsibilities.strip()
        if payload.responsibilities
        else ""
    )

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Position title is required",
        )

    if not description:
        raise HTTPException(
            status_code=400,
            detail="Job Description is required",
        )

    if not required_skills:
        raise HTTPException(
            status_code=400,
            detail="Required skills are required",
        )

    if not education:
        raise HTTPException(
            status_code=400,
            detail="Education requirement is required",
        )

    if not responsibilities:
        raise HTTPException(
            status_code=400,
            detail="Responsibilities are required",
        )

    position = JobPosition(
        title=title,
        description=description,
        required_skills=required_skills,
        education=education,
        experience_required=(
            experience_required
            if experience_required
            else None
        ),
        responsibilities=(
            responsibilities
            if responsibilities
            else None
        ),
        is_active=payload.is_active,
    )

    db.add(position)
    db.commit()
    db.refresh(position)

    return {
        "message": "Job position created successfully",

        "position": {
            "id": position.id,
            "title": position.title,
            "description": position.description,
            "required_skills": position.required_skills,
            "education": position.education,
            "experience_required": position.experience_required,
            "responsibilities": position.responsibilities,
            "is_active": position.is_active,
        },
    }


# =========================================================
# UPDATE POSITION
# =========================================================

@router.put("/positions/{position_id}")
def update_position(
    position_id: int,
    payload: PositionRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    position = (
        db.query(JobPosition)
        .filter(JobPosition.id == position_id)
        .first()
    )

    if not position:
        raise HTTPException(
            status_code=404,
            detail="Job position not found",
        )

    title = payload.title.strip()
    description = payload.description.strip()
    required_skills = payload.required_skills.strip()

    education = (
        payload.education.strip()
        if payload.education
        else ""
    )

    experience_required = (
        payload.experience_required.strip()
        if payload.experience_required
        else ""
    )

    responsibilities = (
        payload.responsibilities.strip()
        if payload.responsibilities
        else ""
    )

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Position title is required",
        )

    if not description:
        raise HTTPException(
            status_code=400,
            detail="Job Description is required",
        )

    if not required_skills:
        raise HTTPException(
            status_code=400,
            detail="Required skills are required",
        )

    if not education:
        raise HTTPException(
            status_code=400,
            detail="Education requirement is required",
        )

    if not responsibilities:
        raise HTTPException(
            status_code=400,
            detail="Responsibilities are required",
        )

    position.title = title
    position.description = description
    position.required_skills = required_skills
    position.education = education

    position.experience_required = (
        experience_required
        if experience_required
        else None
    )

    position.responsibilities = (
        responsibilities
        if responsibilities
        else None
    )

    position.is_active = payload.is_active

    db.commit()
    db.refresh(position)

    return {
        "message": "Job position updated successfully",

        "position": {
            "id": position.id,
            "title": position.title,
            "description": position.description,
            "required_skills": position.required_skills,
            "education": position.education,
            "experience_required": position.experience_required,
            "responsibilities": position.responsibilities,
            "is_active": position.is_active,
        },
    }


# =========================================================
# DELETE POSITION
# =========================================================

@router.delete("/positions/{position_id}")
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    position = (
        db.query(JobPosition)
        .filter(JobPosition.id == position_id)
        .first()
    )

    if not position:
        raise HTTPException(
            status_code=404,
            detail="Job position not found",
        )

    used_by_resume = (
        db.query(Resume)
        .filter(
            Resume.job_position_id == position_id
        )
        .first()
    )

    if used_by_resume:
        raise HTTPException(
            status_code=400,
            detail=(
                "This position is already used by "
                "a candidate and cannot be deleted."
            ),
        )

    db.delete(position)
    db.commit()

    return {
        "message": "Job position deleted successfully"
    }