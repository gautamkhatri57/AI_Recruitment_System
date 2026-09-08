import json
import secrets
from pathlib import Path

import bcrypt

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    InterviewAnswer,
    InterviewQuestion,
    JobPosition,
    Resume,
    ResumeAnalysis,
    User,
)
from app.job import get_all_positions, get_job_description
from app.resume import extract_text_from_file
from app.analyzer import (
    analyze_jd,
    analyze_resume,
    generate_interview_questions,
    evaluate_interview_answer,
)

# ==========================================================
# ADMIN ROUTER
# ==========================================================

from app.admin import router as admin_router


# ==========================================================
# APP
# ==========================================================

app = FastAPI(
    title="AI Recruitment System"
)


# ==========================================================
# CANDIDATE SESSIONS
# ==========================================================

candidate_sessions = {}


# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# ADMIN ROUTER
# ==========================================================

app.include_router(
    admin_router
)


# ==========================================================
# DATABASE
# ==========================================================

def get_db():
    return SessionLocal()


# ==========================================================
# PASSWORD HELPERS
# ==========================================================

def hash_password(password: str) -> str:

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password is too long. "
                "Please use a password of 72 bytes or fewer."
            )
        )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(
    password: str,
    password_hash: str
) -> bool:

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    try:

        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode("utf-8")
        )

    except Exception as error:

        print(
            "PASSWORD VERIFY ERROR:",
            repr(error)
        )

        return False


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "message":
            "AI Recruitment System Backend is running"
    }


# ==========================================================
# CANDIDATE REGISTER
# ==========================================================

@app.post("/auth/register")
def candidate_register(
    name: str,
    email: str,
    phone: str,
    password: str,
):

    db: Session = get_db()

    try:

        name = name.strip()
        email = email.strip().lower()
        phone = phone.strip()
        password = password.strip()

        if not name:

            raise HTTPException(
                status_code=400,
                detail="Name is required."
            )

        if not email:

            raise HTTPException(
                status_code=400,
                detail="Email is required."
            )

        if not phone:

            raise HTTPException(
                status_code=400,
                detail="Phone is required."
            )

        if not password:

            raise HTTPException(
                status_code=400,
                detail="Password is required."
            )

        if len(password) < 6:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must be at least "
                    "6 characters."
                )
            )

        if len(password.encode("utf-8")) > 72:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Password is too long. "
                    "Please use a password of "
                    "72 bytes or fewer."
                )
            )

        existing_user = (
            db.query(User)
            .filter(
                User.email == email
            )
            .first()
        )

        if existing_user:

            raise HTTPException(
                status_code=400,
                detail=(
                    "An account with this "
                    "email already exists."
                )
            )

        password_hash = hash_password(
            password
        )

        user = User(
            full_name=name,
            email=email,
            phone=phone,
            password_hash=password_hash
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        token = secrets.token_urlsafe(32)

        candidate_sessions[token] = {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
        }

        return {

            "message":
                "Registration successful.",

            "token":
                token,

            "candidate": {

                "id":
                    user.id,

                "name":
                    user.full_name,

                "email":
                    user.email,

                "phone":
                    user.phone,
            }
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as error:

        db.rollback()

        print(
            "ERROR /auth/register:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        db.close()


# ==========================================================
# CANDIDATE LOGIN
# ==========================================================

@app.post("/auth/login")
def candidate_login(
    email: str,
    password: str,
):

    db: Session = get_db()

    try:

        email = email.strip().lower()

        if not email:

            raise HTTPException(
                status_code=400,
                detail="Email is required."
            )

        if not password:

            raise HTTPException(
                status_code=400,
                detail="Password is required."
            )

        user = (
            db.query(User)
            .filter(
                User.email == email
            )
            .first()
        )

        if not user:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid email or password."
                )
            )

        password_valid = verify_password(
            password,
            user.password_hash
        )

        if not password_valid:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid email or password."
                )
            )

        token = secrets.token_urlsafe(32)

        candidate_sessions[token] = {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
        }

        return {

            "message":
                "Login successful.",

            "token":
                token,

            "candidate": {

                "id":
                    user.id,

                "name":
                    user.full_name,

                "email":
                    user.email,

                "phone":
                    user.phone,
            }
        }

    except HTTPException:

        raise

    except Exception as error:

        print(
            "ERROR /auth/login:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        db.close()


# ==========================================================
# CANDIDATE LOGOUT
# ==========================================================

@app.post("/auth/logout")
def candidate_logout(
    token: str,
):

    token = token.strip()

    if token in candidate_sessions:

        del candidate_sessions[token]

    return {
        "message":
            "Logout successful."
    }


# ==========================================================
# CANDIDATE POSITIONS
# ==========================================================

@app.get("/positions")
def positions():

    db: Session = get_db()

    try:

        return {
            "positions":
                get_all_positions(db)
        }

    except Exception as error:

        print(
            "ERROR /positions:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        db.close()


# ==========================================================
# JOB DESCRIPTION
# ==========================================================

@app.get("/job")
def get_job(
    position_id: int
):

    db: Session = get_db()

    try:

        job_position = (
            db.query(JobPosition)
            .filter(
                JobPosition.id == position_id,
                JobPosition.is_active == True
            )
            .first()
        )

        if not job_position:

            raise HTTPException(
                status_code=404,
                detail="Job position not found."
            )

        return {

            "id":
                job_position.id,

            "position":
                job_position.title,

            "jd_text":
                job_position.description or "",

            "required_skills":
                job_position.required_skills or "",

            "education":
                getattr(
                    job_position,
                    "education",
                    ""
                ) or "",

            "experience_required":
                job_position.experience_required or "",

            "responsibilities":
                job_position.responsibilities or ""
        }

    except HTTPException:

        raise

    except Exception as error:

        print(
            "ERROR /job:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        db.close()


# ==========================================================
# RESUME ANALYSIS
# ==========================================================

@app.post("/resume/analyze")
async def analyze_uploaded_resume(

    name: str = Form(...),

    email: str = Form(...),

    phone: str = Form(...),

    position: str = Form(...),

    position_id: int = Form(...),

    file: UploadFile = File(...)
):

    db: Session = get_db()

    try:

        job_position = (
            db.query(JobPosition)
            .filter(
                JobPosition.id == position_id,
                JobPosition.is_active == True
            )
            .first()
        )

        if not job_position:

            raise HTTPException(
                status_code=400,
                detail="Invalid or inactive job position."
            )

        if (
            position.strip().lower()
            !=
            job_position.title.strip().lower()
        ):

            raise HTTPException(
                status_code=400,
                detail="Position information does not match."
            )

        jd_text = (
            job_position.description or ""
        ).strip()

        if not jd_text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Job description is not available "
                    "for this position."
                )
            )

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="Resume file is required."
            )

        extension = Path(
            file.filename
        ).suffix.lower()

        if extension not in [
            ".pdf",
            ".docx"
        ]:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only PDF and DOCX "
                    "resumes are allowed."
                )
            )

        file_bytes = await file.read()

        if not file_bytes:

            raise HTTPException(
                status_code=400,
                detail="Uploaded resume is empty."
            )

        resume_text = (
            extract_text_from_file(
                file_bytes,
                file.filename
            )
        )

        if not resume_text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract text "
                    "from resume."
                )
            )

        jd_analysis = analyze_jd(
            jd_text,
            job_position.title
        )

        required_skills = jd_analysis.get(
            "required_skills",
            []
        )

        experience = jd_analysis.get(
            "experience",
            ""
        )

        qualification = jd_analysis.get(
            "qualification",
            ""
        )

        responsibilities = jd_analysis.get(
            "responsibilities",
            []
        )

        if job_position.required_skills:

            db_skills = job_position.required_skills

            try:

                parsed_skills = json.loads(
                    db_skills
                )

                if isinstance(
                    parsed_skills,
                    list
                ):

                    required_skills = parsed_skills

            except Exception:

                required_skills = [
                    skill.strip()
                    for skill in db_skills.split(",")
                    if skill.strip()
                ]

        if job_position.experience_required:

            experience = (
                job_position.experience_required
            )

        if job_position.education:

            qualification = (
                job_position.education
            )

        if job_position.responsibilities:

            responsibilities = [
                item.strip()
                for item in
                job_position.responsibilities.split(
                    "\n"
                )
                if item.strip()
            ]

        user = (
            db.query(User)
            .filter(
                User.email == email.strip().lower()
            )
            .first()
        )

        if not user:

            random_password = (
                secrets.token_urlsafe(16)
            )

            user = User(

                full_name=name.strip(),

                email=email.strip().lower(),

                phone=phone.strip(),

                password_hash=
                    hash_password(
                        random_password
                    )
            )

            db.add(user)

            db.commit()

            db.refresh(user)

        else:

            user.full_name = name.strip()

            user.phone = phone.strip()

            db.commit()

            db.refresh(user)

        safe_filename = (

            f"{user.id}_"

            f"{secrets.token_hex(8)}_"

            f"{file.filename}"
        )

        file_path = (
            UPLOAD_DIR /
            safe_filename
        )

        with open(
            file_path,
            "wb"
        ) as resume_file:

            resume_file.write(
                file_bytes
            )

        resume = Resume(

            user_id=user.id,

            job_position_id=
                job_position.id,

            original_filename=
                file.filename,

            file_path=
                str(file_path)
        )

        db.add(resume)

        db.commit()

        db.refresh(resume)

        resume_analysis = analyze_resume(

            resume_text,

            job_position.title,

            required_skills,

            experience,

            qualification,

            responsibilities
        )

        ats_score = resume_analysis.get(
            "ats_score",
            0
        )

        try:

            ats_score = float(
                ats_score
            )

        except (
            ValueError,
            TypeError
        ):

            ats_score = 0

        ats_score = max(
            0,
            min(
                100,
                ats_score
            )
        )

        strengths_data = {

            "education":
                resume_analysis.get(
                    "education",
                    []
                ),

            "resume_skills":
                resume_analysis.get(
                    "resume_skills",
                    []
                ),

            "matched_skills":
                resume_analysis.get(
                    "matched_skills",
                    []
                ),

            "experience":
                resume_analysis.get(
                    "experience",
                    []
                ),

            "qualification_match":
                resume_analysis.get(
                    "qualification_match",
                    False
                ),

            "projects":
                resume_analysis.get(
                    "projects",
                    []
                ),

            "certifications":
                resume_analysis.get(
                    "certifications",
                    []
                ),

            "responsibility_match":
                resume_analysis.get(
                    "responsibility_match",
                    []
                )
        }

        weaknesses_data = {

            "missing_skills":
                resume_analysis.get(
                    "missing_skills",
                    []
                ),

            "experience_match":
                resume_analysis.get(
                    "experience_match",
                    False
                )
        }

        suggestions_data = {

            "recommendation":
                resume_analysis.get(
                    "recommendation",
                    ""
                )
        }

        analysis_record = ResumeAnalysis(

            resume_id=resume.id,

            score=int(
                ats_score
            ),

            strengths=json.dumps(
                strengths_data,
                ensure_ascii=False
            ),

            weaknesses=json.dumps(
                weaknesses_data,
                ensure_ascii=False
            ),

            suggestions=json.dumps(
                suggestions_data,
                ensure_ascii=False
            ),

            interview_score=None,

            overall_score=None,

            final_recommendation=None
        )

        db.add(
            analysis_record
        )

        candidate_profile = {

            "candidate_name":
                resume_analysis.get(
                    "candidate_name",
                    name
                ),

            "email":
                resume_analysis.get(
                    "email",
                    email
                ),

            "phone":
                resume_analysis.get(
                    "phone",
                    phone
                ),

            "education":
                resume_analysis.get(
                    "education",
                    []
                ),

            "resume_skills":
                resume_analysis.get(
                    "resume_skills",
                    []
                ),

            "matched_skills":
                resume_analysis.get(
                    "matched_skills",
                    []
                ),

            "experience":
                resume_analysis.get(
                    "experience",
                    []
                ),

            "projects":
                resume_analysis.get(
                    "projects",
                    []
                ),

            "certifications":
                resume_analysis.get(
                    "certifications",
                    []
                )
        }

        job_requirements = {

            "required_skills":
                required_skills,

            "experience":
                experience,

            "qualification":
                qualification,

            "responsibilities":
                responsibilities
        }

        interview_data = (
            generate_interview_questions(

                job_position.title,

                job_requirements,

                candidate_profile
            )
        )

        questions = interview_data.get(
            "questions",
            []
        )

        if not questions:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Interview questions "
                    "could not be generated."
                )
            )

        saved_questions = []

        for question_data in questions:

            question_record = (
                InterviewQuestion(

                    resume_id=resume.id,

                    question=json.dumps(
                        question_data,
                        ensure_ascii=False
                    )
                )
            )

            db.add(
                question_record
            )

            db.flush()

            saved_questions.append({

                "id":
                    question_record.id,

                **question_data

            })

        db.commit()

        return {

            "message":
                (
                    "Application submitted "
                    "successfully. "
                    "Interview questions "
                    "generated."
                ),

            "application_id":
                resume.id,

            "filename":
                file.filename,

            "position":
                job_position.title,

            "position_id":
                job_position.id,

            "interview_questions": {

                "questions":
                    saved_questions
            }
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as error:

        db.rollback()

        print(
            "ERROR /resume/analyze:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        db.close()


# ==========================================================
# INTERVIEW SUBMISSION
# ==========================================================

@app.post("/interview/submit")
async def submit_interview(
    data: dict
):

    db: Session = get_db()

    try:

        print(
            "\n========== INTERVIEW SUBMIT =========="
        )

        print(
            "RECEIVED DATA:",
            data
        )

        application_id = data.get(
            "application_id"
        )

        answers = data.get(
            "answers"
        )

        print(
            "APPLICATION ID:",
            application_id
        )

        print(
            "ANSWERS:",
            answers
        )

        print(
            "ANSWERS COUNT:",
            len(answers)
            if isinstance(
                answers,
                list
            )
            else "NOT LIST"
        )

        if not application_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "application_id is required."
                )
            )

        if not isinstance(
            answers,
            list
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "answers must be a list."
                )
            )

        if len(answers) == 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No interview answers "
                    "were submitted."
                )
            )

        resume = (

            db.query(Resume)

            .filter(
                Resume.id == application_id
            )

            .first()
        )

        if not resume:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Application not found."
                )
            )

        questions = (

            db.query(
                InterviewQuestion
            )

            .filter(
                InterviewQuestion.resume_id
                == resume.id
            )

            .order_by(
                InterviewQuestion.id.asc()
            )

            .all()
        )

        if not questions:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Interview questions "
                    "not found."
                )
            )

        print(
            "QUESTIONS FOUND:",
            len(questions)
        )

        question_lookup = {

            question.id:
                question

            for question in questions
        }

        saved_count = 0

        evaluated_count = 0

        collected_scores = []

        for answer_item in answers:

            if not isinstance(
                answer_item,
                dict
            ):

                print(
                    "SKIPPING INVALID ANSWER:",
                    answer_item
                )

                continue

            question_id = answer_item.get(
                "question_id"
            )

            answer_value = answer_item.get(
                "answer"
            )

            print(
                "\nPROCESSING:",
                question_id,
                answer_value
            )

            if question_id is None:

                print(
                    "SKIPPED: question_id missing"
                )

                continue

            question = question_lookup.get(
                question_id
            )

            if not question:

                print(
                    "SKIPPED: question not found:",
                    question_id
                )

                continue

            if isinstance(
                answer_value,
                (dict, list)
            ):

                answer_text = json.dumps(
                    answer_value,
                    ensure_ascii=False
                )

            elif answer_value is None:

                answer_text = ""

            else:

                answer_text = str(
                    answer_value
                ).strip()

            if not answer_text:

                print(
                    "SKIPPED: empty answer:",
                    question.id
                )

                continue

            try:

                question_data = json.loads(
                    question.question
                )

            except (
                json.JSONDecodeError,
                TypeError
            ):

                question_data = {

                    "question":
                        question.question,

                    "type":
                        "short_answer",

                    "options":
                        []
                }

            question_text = str(
                question_data.get(
                    "question",
                    ""
                )
            ).strip()

            question_type = str(
                question_data.get(
                    "type",
                    "short_answer"
                )
            ).strip().lower()

            options = question_data.get(
                "options",
                []
            )

            if not isinstance(
                options,
                list
            ):

                options = []

            print(
                "AI EVALUATION STARTED:",
                question.id
            )

            evaluation_result = (
                evaluate_interview_answer(

                    question=question_text,

                    answer=answer_text,

                    question_type=question_type,

                    options=options
                )
            )

            answer_score = (
                evaluation_result.get(
                    "score",
                    0
                )
            )

            evaluation_text = (
                evaluation_result.get(
                    "evaluation",
                    ""
                )
            )

            try:

                answer_score = int(
                    float(answer_score)
                )

            except (
                ValueError,
                TypeError
            ):

                answer_score = 0

            answer_score = max(
                0,
                min(
                    10,
                    answer_score
                )
            )

            print(
                "AI SCORE:",
                answer_score
            )

            print(
                "AI EVALUATION:",
                evaluation_text
            )

            existing_answer = (

                db.query(
                    InterviewAnswer
                )

                .filter(
                    InterviewAnswer.question_id
                    == question.id
                )

                .first()
            )

            if existing_answer:

                existing_answer.answer = (
                    answer_text
                )

                existing_answer.score = (
                    answer_score
                )

                existing_answer.evaluation = (
                    evaluation_text
                )

                print(
                    "UPDATED ANSWER:",
                    existing_answer.id
                )

            else:

                answer_record = InterviewAnswer(

                    question_id=question.id,

                    answer=answer_text,

                    evaluation=evaluation_text,

                    score=answer_score
                )

                db.add(
                    answer_record
                )

                print(
                    "CREATED + EVALUATED ANSWER:",
                    question.id
                )

            saved_count += 1

            evaluated_count += 1

            collected_scores.append(
                answer_score
            )

        if saved_count == 0:

            db.rollback()

            raise HTTPException(
                status_code=400,
                detail=(
                    "No valid interview answers "
                    "could be saved."
                )
            )

        if evaluated_count == 0:

            db.rollback()

            raise HTTPException(
                status_code=400,
                detail=(
                    "No interview answers "
                    "could be evaluated."
                )
            )

        # ==================================================
        # INTERVIEW SCORE
        # ==================================================

        total_interview_score = sum(
            collected_scores
        )

        average_interview_score = (
            total_interview_score
            /
            len(collected_scores)
        )

        interview_score = round(
            (
                average_interview_score
                /
                10
            )
            *
            100
        )

        interview_score = max(
            0,
            min(
                100,
                interview_score
            )
        )

        # ==================================================
        # RESUME SCORE
        # ==================================================

        analysis_record = (

            db.query(
                ResumeAnalysis
            )

            .filter(
                ResumeAnalysis.resume_id
                == resume.id
            )

            .first()
        )

        if not analysis_record:

            db.rollback()

            raise HTTPException(
                status_code=404,
                detail=(
                    "Resume analysis "
                    "not found."
                )
            )

        resume_score = (
            analysis_record.score
        )

        if resume_score is None:

            resume_score = 0

        try:

            resume_score = int(
                float(resume_score)
            )

        except (
            ValueError,
            TypeError
        ):

            resume_score = 0

        resume_score = max(
            0,
            min(
                100,
                resume_score
            )
        )

        # ==================================================
        # OVERALL SCORE
        # ==========================================================

        overall_score = round(

            (
                resume_score
                *
                0.60
            )
            +
            (
                interview_score
                *
                0.40
            )
        )

        overall_score = max(
            0,
            min(
                100,
                overall_score
            )
        )

        # ==================================================
        # FINAL RECOMMENDATION
        # ==========================================================

        if overall_score >= 80:

            final_recommendation = (
                "Strongly Recommended"
            )

        elif overall_score >= 65:

            final_recommendation = (
                "Recommended"
            )

        elif overall_score >= 50:

            final_recommendation = (
                "Maybe"
            )

        else:

            final_recommendation = (
                "Not Recommended"
            )

        # ==================================================
        # SAVE SCORES
        # ==========================================================

        analysis_record.interview_score = (
            interview_score
        )

        analysis_record.overall_score = (
            overall_score
        )

        analysis_record.final_recommendation = (
            final_recommendation
        )

        db.commit()

        print(
            "\n========== INTERVIEW COMPLETE =========="
        )

        print(
            "ANSWERS SAVED:",
            saved_count
        )

        print(
            "INTERVIEW SCORE:",
            interview_score
        )

        print(
            "RESUME SCORE:",
            resume_score
        )

        print(
            "OVERALL SCORE:",
            overall_score
        )

        print(
            "FINAL RECOMMENDATION:",
            final_recommendation
        )

        print(
            "========================================\n"
        )

        # ==================================================
        # FINAL RESPONSE WITH SCORES
        # ==================================================

        return {

            "message":
                "Interview submitted successfully.",

            "application_id":
                resume.id,

            "answers_saved":
                saved_count,

            "answers_evaluated":
                evaluated_count,

            "resume_score":
                resume_score,

            "interview_score":
                interview_score,

            "overall_score":
                overall_score,

            "final_recommendation":
                final_recommendation
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as error:

        db.rollback()

        print(
            "ERROR /interview/submit:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        db.close()