from pathlib import Path
import re

from sqlalchemy.orm import Session

from app.models import JobPosition


# ==========================================================
# PATH CONFIG
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

JOBS_FILE = BASE_DIR / "jobs" / "jobs.pdf"


# ==========================================================
# LEGACY POSITION LIST
# ==========================================================
# Kept only for the old PDF-based job description functions.
# Candidate position list is now fetched from the database.

POSITIONS = [
    "Receptionist/Back office executive",
    "Legal Advisor/Executive",
    "Graphic Designer",
    "Content Creator",
    "Video Editor",
    "Content Writer",
    "CRM / Telecalling",
    "Documents Verification Executive",
    "Legal Intern",
    "Accountant / Accounts Executive",
    "Company Secretary",
    "Sales Intern",
    "HR Intern",
    "Accounting Intern",
    "Social Media Marketing Intern",
    "Sales Manager/Executive",
    "HR Manager/Executive",
]


# ==========================================================
# NORMALIZE TEXT
# ==========================================================

def normalize_text(text: str) -> str:
    """
    Normalize PDF text so position headings can be found
    reliably even if spacing or line breaks are different.
    """

    if not text:
        return ""

    text = text.replace("\r", "\n")

    # Normalize multiple spaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Normalize excessive new lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ==========================================================
# LOAD JOB PDF
# ==========================================================

def load_jobs_pdf() -> str:

    if not JOBS_FILE.exists():
        raise FileNotFoundError(
            f"Job description PDF not found: {JOBS_FILE}"
        )

    try:

        from PyPDF2 import PdfReader

        reader = PdfReader(
            str(JOBS_FILE)
        )

        text_parts = []

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text_parts.append(
                    page_text
                )

        full_text = "\n".join(
            text_parts
        )

        full_text = normalize_text(
            full_text
        )

        if not full_text:
            raise ValueError(
                "Job description PDF is empty or text could not be extracted."
            )

        return full_text

    except Exception as error:

        raise ValueError(
            f"Failed to read jobs PDF: {error}"
        )


# ==========================================================
# FIND POSITION SECTION
# ==========================================================

def find_position_section(
    full_text: str,
    position: str
) -> str:

    if not full_text:
        return ""

    if not position:
        return ""

    # ------------------------------------------------------
    # Exact search first
    # ------------------------------------------------------

    position_index = full_text.lower().find(
        position.lower()
    )

    if position_index == -1:

        # Try normalized comparison
        normalized_position = re.sub(
            r"\s+",
            " ",
            position.strip().lower()
        )

        lines = full_text.splitlines()

        position_index = -1

        for index, line in enumerate(lines):

            normalized_line = re.sub(
                r"\s+",
                " ",
                line.strip().lower()
            )

            if normalized_position in normalized_line:

                position_index = index

                break

        if position_index != -1:

            section_lines = lines[
                position_index:
            ]

            return normalize_text(
                "\n".join(section_lines)
            )

        return ""

    # ------------------------------------------------------
    # Find next known legacy position
    # ------------------------------------------------------

    start_index = position_index + len(
        position
    )

    next_index = len(full_text)

    for other_position in POSITIONS:

        if other_position.lower() == position.lower():
            continue

        index = full_text.lower().find(
            other_position.lower(),
            start_index
        )

        if index != -1 and index < next_index:

            next_index = index

    section = full_text[
        position_index:next_index
    ]

    return normalize_text(
        section
    )


# ==========================================================
# GET JOB DESCRIPTION FROM LEGACY PDF
# ==========================================================

def get_job_description(
    position: str
) -> dict:

    if position not in POSITIONS:

        raise ValueError(
            f"Invalid job position: {position}"
        )

    full_text = load_jobs_pdf()

    jd_text = find_position_section(
        full_text,
        position
    )

    if not jd_text:

        raise ValueError(
            f"Job description not found for position: {position}"
        )

    return {
        "position": position,
        "jd_text": jd_text
    }


# ==========================================================
# GET ALL POSITIONS
# ==========================================================
# NEW SYSTEM
#
# Positions are fetched from PostgreSQL.
#
# Admin creates:
#   Legal Executive
#   Content Writer
#   etc.
#
# They are stored in:
#   job_positions
#
# Only active positions are returned to candidates.
# ==========================================================

def get_all_positions(db: Session):

    positions = (
        db.query(JobPosition)
        .filter(
            JobPosition.is_active == True
        )
        .order_by(
            JobPosition.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": position.id,
            "title": position.title,
            "description": position.description or "",
            "required_skills": position.required_skills or "",
            "education": (
                position.education
                if hasattr(position, "education")
                else ""
            ) or "",
            "experience_required": (
                position.experience_required or ""
            ),
            "responsibilities": (
                position.responsibilities or ""
            ),
            "is_active": bool(
                position.is_active
            ),
        }
        for position in positions
    ]