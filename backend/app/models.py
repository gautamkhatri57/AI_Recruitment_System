from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


# =========================================================
# USER / CANDIDATE
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    full_name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    phone = Column(
        String(20),
        nullable=True
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    resumes = relationship(
        "Resume",
        back_populates="user"
    )


# =========================================================
# JOB POSITION
# =========================================================

class JobPosition(Base):
    __tablename__ = "job_positions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String(150),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    required_skills = Column(
        Text,
        nullable=False
    )

    education = Column(
        Text,
        nullable=True
    )

    experience_required = Column(
        String(100),
        nullable=True
    )

    responsibilities = Column(
        Text,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    resumes = relationship(
        "Resume",
        back_populates="job_position"
    )


# =========================================================
# RESUME
# =========================================================

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    job_position_id = Column(
        Integer,
        ForeignKey("job_positions.id"),
        nullable=False
    )

    original_filename = Column(
        String(255),
        nullable=False
    )

    file_path = Column(
        String(500),
        nullable=False
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="resumes"
    )

    job_position = relationship(
        "JobPosition",
        back_populates="resumes"
    )

    analysis = relationship(
        "ResumeAnalysis",
        back_populates="resume",
        uselist=False
    )

    interview_questions = relationship(
        "InterviewQuestion",
        back_populates="resume"
    )


# =========================================================
# RESUME ANALYSIS
# =========================================================

class ResumeAnalysis(Base):
    __tablename__ = "resume_analysis"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    resume_id = Column(
        Integer,
        ForeignKey("resumes.id"),
        nullable=False
    )

    score = Column(
        Integer
    )

    strengths = Column(
        Text
    )

    weaknesses = Column(
        Text
    )

    suggestions = Column(
        Text
    )

    interview_score = Column(
        Integer
    )

    overall_score = Column(
        Integer
    )

    final_recommendation = Column(
        String(50)
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    resume = relationship(
        "Resume",
        back_populates="analysis"
    )


# =========================================================
# INTERVIEW QUESTION
# =========================================================

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    resume_id = Column(
        Integer,
        ForeignKey("resumes.id"),
        nullable=False
    )

    question = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    resume = relationship(
        "Resume",
        back_populates="interview_questions"
    )

    answers = relationship(
        "InterviewAnswer",
        back_populates="question"
    )


# =========================================================
# INTERVIEW ANSWER
# =========================================================

class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    question_id = Column(
        Integer,
        ForeignKey("interview_questions.id"),
        nullable=False
    )

    answer = Column(
        Text
    )

    evaluation = Column(
        Text
    )

    score = Column(
        Integer
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    question = relationship(
        "InterviewQuestion",
        back_populates="answers"
    )


# =========================================================
# ADMIN
# =========================================================

class Admin(Base):
    __tablename__ = "admins"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    full_name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )