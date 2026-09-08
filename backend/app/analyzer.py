import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


# ==========================================================
# CONFIG
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        f"GROQ_API_KEY missing. Checked: {ENV_FILE}"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "openai/gpt-oss-120b"


# ==========================================================
# AI REQUEST
# ==========================================================

def ask_ai(prompt):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """
You are an expert HR recruiter, ATS specialist,
Job Description analyst and professional interviewer.

IMPORTANT RULES:

1. Read the complete provided content.
2. Never invent information.
3. Never assume information that is not present.
4. Use semantic understanding.
5. Return ONLY valid JSON.
6. Never use Markdown.
7. Never use ```json.
8. Always return COMPLETE JSON.
9. Never stop in the middle of an array.
10. Never stop in the middle of an object.
11. Always close all JSON brackets.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=12000
        )

        text = response.choices[0].message.content.strip()

        if not text:
            raise ValueError(
                "AI returned an empty response."
            )

        # Remove markdown code fences if AI adds them
        if text.startswith("```json"):
            text = text[7:]

        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}")

        if start == -1:
            raise ValueError(
                f"AI did not return JSON:\n{text}"
            )

        if end == -1 or end <= start:
            raise ValueError(
                "AI returned incomplete JSON."
            )

        json_text = text[start:end + 1]

        try:
            return json.loads(json_text)

        except json.JSONDecodeError as error:
            print("\n========== INVALID AI RESPONSE ==========")
            print(text)
            print("=========================================\n")

            raise ValueError(
                f"AI returned invalid JSON: {error}"
            )

    except Exception as error:
        raise ValueError(
            f"AI request failed: {error}"
        )


# ==========================================================
# JOB DESCRIPTION ANALYSIS
# ==========================================================

def analyze_jd(jd_text, position):

    prompt = f"""
Analyze the following Job Description.

POSITION:
{position}

JOB DESCRIPTION:
{jd_text}

Return ONLY valid JSON in this exact format:

{{
    "position": "{position}",
    "required_skills": [],
    "experience": "",
    "qualification": "",
    "responsibilities": []
}}

RULES:

- required_skills must be an array of strings.
- responsibilities must be an array of strings.
- experience must be a string.
- qualification must be a string.
- Do not invent requirements.
"""

    result = ask_ai(prompt)

    if not isinstance(result, dict):
        raise ValueError(
            "JD analysis returned invalid data."
        )

    result["position"] = position

    if not isinstance(
        result.get("required_skills"),
        list
    ):
        result["required_skills"] = []

    if not result.get("experience"):
        result["experience"] = "Not specified"

    if not result.get("qualification"):
        result["qualification"] = "Not specified"

    if not isinstance(
        result.get("responsibilities"),
        list
    ):
        result["responsibilities"] = []

    return result


# ==========================================================
# RESUME ANALYSIS
# ==========================================================

def analyze_resume(
    resume_text,
    position,
    required_skills,
    experience,
    qualification,
    responsibilities
):

    prompt = f"""
Analyze the candidate resume against the selected job position.

POSITION:
{position}

JOB REQUIREMENTS:

Required Skills:
{json.dumps(required_skills, ensure_ascii=False)}

Experience:
{experience}

Qualification:
{qualification}

Responsibilities:
{json.dumps(responsibilities, ensure_ascii=False)}

CANDIDATE RESUME:
{resume_text}

Return ONLY valid JSON using EXACTLY this structure:

{{
    "candidate_name": "",
    "email": "",
    "phone": "",
    "education": [],
    "resume_skills": [],
    "matched_skills": [],
    "missing_skills": [],
    "experience": [],
    "experience_match": false,
    "qualification_match": false,
    "projects": [],
    "certifications": [],
    "responsibility_match": [],
    "ats_score": 0,
    "recommendation": ""
}}

RULES:

- Extract candidate_name only from the resume.
- Extract email only from the resume.
- Extract phone only from the resume.
- Education must be an array.
- Resume skills must contain skills found in the resume.
- Matched skills must be relevant to the job.
- Missing skills must be relevant required skills not demonstrated.
- Experience must contain actual experience from the resume.
- experience_match must be true or false.
- qualification_match must be true or false.
- Projects must contain actual projects only.
- Certifications must contain actual certifications only.
- responsibility_match must contain responsibilities demonstrated by the candidate.
- ats_score must be a number between 0 and 100.
- recommendation must be a short recruiter recommendation.
- Never invent information.
- Return COMPLETE JSON.
"""

    result = ask_ai(prompt)

    if not isinstance(result, dict):
        raise ValueError(
            "Resume analysis returned invalid data."
        )

    # Safe defaults
    if not isinstance(result.get("education"), list):
        result["education"] = []

    if not isinstance(result.get("resume_skills"), list):
        result["resume_skills"] = []

    if not isinstance(result.get("matched_skills"), list):
        result["matched_skills"] = []

    if not isinstance(result.get("missing_skills"), list):
        result["missing_skills"] = []

    if not isinstance(result.get("experience"), list):
        result["experience"] = []

    if not isinstance(result.get("projects"), list):
        result["projects"] = []

    if not isinstance(result.get("certifications"), list):
        result["certifications"] = []

    if not isinstance(result.get("responsibility_match"), list):
        result["responsibility_match"] = []

    # ATS score
    try:
        score = float(result.get("ats_score", 0))
        result["ats_score"] = max(
            0,
            min(100, score)
        )
    except (ValueError, TypeError):
        result["ats_score"] = 0

    return result


# ==========================================================
# INTERVIEW QUESTION GENERATION
# ==========================================================

def generate_interview_questions(
    position,
    job_requirements,
    candidate_profile
):

    prompt = f"""
You are an expert HR interviewer.

Generate EXACTLY 10 interview assessment questions
for the candidate.

POSITION:
{position}

JOB REQUIREMENTS:
{json.dumps(
    job_requirements,
    ensure_ascii=False
)}

CANDIDATE PROFILE:
{candidate_profile}

IMPORTANT:

Do NOT generate 10 long-answer questions.

The interview must be a MIXED assessment.

Use these question types:

- mcq
- situational_mcq
- yes_no
- rating
- short_answer

Recommended distribution:

- 3 mcq
- 2 situational_mcq
- 2 yes_no
- 2 rating
- 1 short_answer

Total = EXACTLY 10 questions.

==========================================================
QUESTION TYPE RULES
==========================================================

MCQ:

- Exactly 4 options.
- One best answer.
- Options must be realistic.
- Do not provide the correct answer.

Example:

{{
    "question": "Which approach is best for handling multiple urgent tasks?",
    "type": "mcq",
    "options": [
        "Prioritize based on urgency and importance",
        "Complete the easiest task first",
        "Wait for someone to decide",
        "Handle tasks randomly"
    ]
}}

==========================================================

SITUATIONAL MCQ:

- Give a realistic workplace situation.
- Exactly 4 options.
- One best answer.
- Do not provide the correct answer.

==========================================================

YES / NO:

Exactly:

{{
    "question": "Have you previously worked with HRMS software?",
    "type": "yes_no",
    "options": [
        "Yes",
        "No"
    ]
}}

==========================================================

RATING:

Candidate rates themselves from 1 to 5.

Use:

{{
    "question": "How confident are you in handling employee documentation?",
    "type": "rating",
    "min": 1,
    "max": 5
}}

Do NOT provide options.

==========================================================

SHORT ANSWER:

Only one short-answer question.

Candidate should answer in approximately 1-3 sentences.

Example:

{{
    "question": "Briefly describe your most relevant experience.",
    "type": "short_answer"
}}

==========================================================

IMPORTANT QUESTION RULES:

- Questions must be relevant to the selected position.
- Questions should consider the candidate's resume.
- Questions should test practical job suitability.
- Avoid unnecessary generic questions.
- Avoid repeating questions.
- Avoid long essay questions.
- Exactly 10 questions.
- Do not include scores.
- Do not include correct answers.
- Do not include explanations.
- Do not use Markdown.

==========================================================
RETURN FORMAT
==========================================================

Return ONLY valid JSON:

{{
    "questions": [
        {{
            "question": "",
            "type": "mcq",
            "options": [
                "",
                "",
                "",
                ""
            ]
        }},
        {{
            "question": "",
            "type": "situational_mcq",
            "options": [
                "",
                "",
                "",
                ""
            ]
        }},
        {{
            "question": "",
            "type": "yes_no",
            "options": [
                "Yes",
                "No"
            ]
        }},
        {{
            "question": "",
            "type": "rating",
            "min": 1,
            "max": 5
        }},
        {{
            "question": "",
            "type": "short_answer"
        }}
    ]
}}

FINAL RULE:

Return EXACTLY 10 complete questions.

Do not stop early.

Make sure the JSON is completely closed.
"""

    result = ask_ai(prompt)

    if not isinstance(result, dict):
        raise ValueError(
            "Interview question generation returned invalid data."
        )

    questions = result.get("questions", [])

    if not isinstance(questions, list):
        raise ValueError(
            "Interview questions must be a list."
        )

    clean_questions = []

    allowed_types = {
        "mcq",
        "situational_mcq",
        "yes_no",
        "rating",
        "short_answer"
    }

    for item in questions:

        if not isinstance(item, dict):
            continue

        question = str(
            item.get("question", "")
        ).strip()

        question_type = str(
            item.get("type", "")
        ).strip().lower()

        if not question:
            continue

        if question_type not in allowed_types:
            continue

        # MCQ / Situational MCQ
        if question_type in {
            "mcq",
            "situational_mcq"
        }:

            options = item.get("options", [])

            if not isinstance(options, list):
                continue

            options = [
                str(option).strip()
                for option in options
                if str(option).strip()
            ]

            if len(options) != 4:
                continue

            clean_questions.append({
                "question": question,
                "type": question_type,
                "options": options
            })

        # Yes / No
        elif question_type == "yes_no":

            clean_questions.append({
                "question": question,
                "type": "yes_no",
                "options": [
                    "Yes",
                    "No"
                ]
            })

        # Rating
        elif question_type == "rating":

            clean_questions.append({
                "question": question,
                "type": "rating",
                "min": 1,
                "max": 5
            })

        # Short Answer
        elif question_type == "short_answer":

            clean_questions.append({
                "question": question,
                "type": "short_answer"
            })

    if len(clean_questions) < 10:
        raise ValueError(
            f"AI generated only "
            f"{len(clean_questions)} valid questions. "
            f"Expected exactly 10."
        )

    return {
        "questions": clean_questions[:10]
    }

# ==========================================================
# INTERVIEW ANSWER EVALUATION
# ==========================================================

def evaluate_interview_answer(
    question,
    answer,
    question_type,
    options=None
):
    """
    Evaluate a candidate's interview answer using AI.

    Score:
        0-10

    Returns:
        {
            "score": 0-10,
            "evaluation": "..."
        }
    """

    options = options or []

    prompt = f"""
Evaluate the candidate's answer to the interview question.

QUESTION:
{question}

QUESTION TYPE:
{question_type}

OPTIONS:
{json.dumps(options, ensure_ascii=False)}

CANDIDATE ANSWER:
{answer}

==========================================================
EVALUATION RULES
==========================================================

Evaluate the answer fairly and professionally.

For MCQ and situational_mcq:
- Check whether the selected answer is the best option.
- Use the question and all provided options to determine correctness.
- Do not assume the candidate selected an option that they did not provide.

For yes_no:
- Evaluate whether the answer is relevant and consistent with the question.
- Do not mark a candidate wrong simply because the answer is "Yes" or "No".
- This is a candidate-experience/background response, not necessarily a right/wrong question.

For rating:
- The candidate gives a self-rating from 1 to 5.
- Convert the rating reasonably to a score out of 10.
- Rating 1 = approximately 2/10
- Rating 2 = approximately 4/10
- Rating 3 = approximately 6/10
- Rating 4 = approximately 8/10
- Rating 5 = 10/10
- Do not judge the candidate's confidence as factually wrong.

For short_answer:
- Evaluate relevance.
- Evaluate clarity.
- Evaluate practical understanding.
- Evaluate whether the answer addresses the question.
- Do not require a specific wording.

==========================================================
SCORING
==========================================================

Return a score from 0 to 10.

General guidance:

9-10 = Excellent
7-8  = Good
5-6  = Average
3-4  = Weak
0-2  = Very poor / irrelevant

Do not give everyone the same score.

==========================================================
EVALUATION TEXT
==========================================================

Provide concise professional recruiter feedback.

The evaluation should explain:
- what was good or bad about the answer
- whether it was relevant
- what could be improved

Keep the evaluation within 2-3 sentences.

Do not mention hidden scoring rules.

==========================================================
RETURN FORMAT
==========================================================

Return ONLY valid JSON.

{{
    "score": 0,
    "evaluation": ""
}}

IMPORTANT:
- score must be an integer from 0 to 10.
- evaluation must be a string.
- Never return Markdown.
- Never return additional fields.
"""

    result = ask_ai(prompt)

    if not isinstance(result, dict):
        raise ValueError(
            "Interview answer evaluation returned invalid data."
        )

    # ------------------------------------------------------
    # SCORE
    # ------------------------------------------------------

    try:
        score = int(float(result.get("score", 0)))
    except (ValueError, TypeError):
        score = 0

    score = max(0, min(10, score))

    # ------------------------------------------------------
    # EVALUATION
    # ------------------------------------------------------

    evaluation = result.get(
        "evaluation",
        "No evaluation was provided."
    )

    if not isinstance(evaluation, str):
        evaluation = str(evaluation)

    evaluation = evaluation.strip()

    if not evaluation:
        evaluation = "No evaluation was provided."

    return {
        "score": score,
        "evaluation": evaluation
    }