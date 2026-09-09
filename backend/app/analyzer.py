98t23fuyy4import os
import json
import time
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

# Reduced to avoid Groq TPM rate-limit problems
MAX_TOKENS = 4000

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


# ==========================================================
# AI REQUEST
# ==========================================================

def ask_ai(prompt):
    last_error = None

    for attempt in range(MAX_RETRIES):

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
                max_tokens=MAX_TOKENS
            )

            text = response.choices[0].message.content.strip()

            if not text:
                raise ValueError(
                    "AI returned an empty response."
                )

            # Remove Markdown code fences
            if text.startswith("```json"):
                text = text[7:]

            elif text.startswith("```"):
                text = text[3:]

            if text.endswith("```"):
                text = text[:-3]

            text = text.strip()

            # Locate JSON object
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

                print(
                    "\n========== INVALID AI RESPONSE =========="
                )
                print(text)
                print(
                    "=========================================\n"
                )

                raise ValueError(
                    f"AI returned invalid JSON: {error}"
                )

        except Exception as error:

            last_error = error
            error_text = str(error)

            # Retry rate-limit errors
            if (
                "429" in error_text
                or "rate_limit" in error_text.lower()
            ):

                if attempt < MAX_RETRIES - 1:

                    wait_time = (
                        RETRY_DELAY_SECONDS *
                        (attempt + 1)
                    )

                    print(
                        f"Groq rate limit reached. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)
                    continue

            break

    raise ValueError(
        f"AI request failed: {last_error}"
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
{json.dumps(
    required_skills,
    ensure_ascii=False
)}

Experience:
{experience}

Qualification:
{qualification}

Responsibilities:
{json.dumps(
    responsibilities,
    ensure_ascii=False
)}

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

    if not isinstance(
        result.get("education"),
        list
    ):
        result["education"] = []

    if not isinstance(
        result.get("resume_skills"),
        list
    ):
        result["resume_skills"] = []

    if not isinstance(
        result.get("matched_skills"),
        list
    ):
        result["matched_skills"] = []

    if not isinstance(
        result.get("missing_skills"),
        list
    ):
        result["missing_skills"] = []

    if not isinstance(
        result.get("experience"),
        list
    ):
        result["experience"] = []

    if not isinstance(
        result.get("projects"),
        list
    ):
        result["projects"] = []

    if not isinstance(
        result.get("certifications"),
        list
    ):
        result["certifications"] = []

    if not isinstance(
        result.get("responsibility_match"),
        list
    ):
        result["responsibility_match"] = []

    try:

        score = float(
            result.get(
                "ats_score",
                0
            )
        )

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
    candidate_profile,
    previous_questions=None
):

    if previous_questions is None:
        previous_questions = []

    # Keep only previous question text
    previous_question_text = []

    for item in previous_questions:

        if isinstance(item, dict):

            question = item.get(
                "question",
                ""
            )

            if question:
                previous_question_text.append(
                    str(question).strip()
                )

        elif isinstance(item, str):

            if item.strip():
                previous_question_text.append(
                    item.strip()
                )

    # Limit history to avoid huge prompts
    previous_question_text = (
        previous_question_text[-50:]
    )

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


==========================================================
IMPORTANT: QUESTION VARIATION
==========================================================

Every candidate should NOT receive the exact same
interview questions for the same position.

Generate fresh and varied questions.

Questions should vary by:

- wording
- scenario
- skill being tested
- practical situation
- candidate experience
- responsibilities
- difficulty
- examples
- business context

DO NOT copy any question from the previous-question list.

DO NOT create a question that is essentially the same
question with only a few words changed.

Previous questions are listed below.

PREVIOUS QUESTIONS:
{json.dumps(
    previous_question_text,
    ensure_ascii=False
)}

If the previous-question list is empty, generate
a completely fresh set.

If previous questions exist, make sure ALL 10 new
questions are meaningfully different.


==========================================================
INTERVIEW STRUCTURE
==========================================================

Generate EXACTLY 10 questions.

Use this distribution:

- 3 mcq
- 2 situational_mcq
- 2 yes_no
- 2 rating
- 1 short_answer

TOTAL = EXACTLY 10.


==========================================================
MCQ
==========================================================

Create 3 multiple-choice questions.

Rules:

- Exactly 4 options.
- One best answer.
- Options must be realistic.
- Do not include the correct answer.
- Questions must be position-specific.


==========================================================
SITUATIONAL MCQ
==========================================================

Create 2 realistic workplace situations.

Rules:

- Exactly 4 options.
- One best answer.
- Situation must be relevant to the position.
- Do not include the correct answer.


==========================================================
YES / NO
==========================================================

Create 2 questions.

Use exactly:

"options": [
    "Yes",
    "No"
]

These should preferably check:

- previous experience
- exposure
- familiarity
- tools
- responsibilities


==========================================================
RATING
==========================================================

Create 2 self-assessment questions.

IMPORTANT:

DO NOT use numeric 1-5 rating.

The candidate should choose from:

- Excellent
- Good
- Average
- Poor
- Very Poor

Use this exact structure:

{{
    "question": "How would you rate your confidence in handling client communication?",
    "type": "rating",
    "options": [
        "Excellent",
        "Good",
        "Average",
        "Poor",
        "Very Poor"
    ]
}}

Questions should be relevant to the selected position.


==========================================================
SHORT ANSWER
==========================================================

Create exactly 1 short-answer question.

Candidate should answer in approximately 1-3 sentences.

It should be relevant to:

- candidate experience
- job responsibilities
- problem solving
- position-specific work


==========================================================
QUALITY RULES
==========================================================

Every question must:

- Be relevant to the selected position.
- Consider the candidate profile.
- Test actual job suitability.
- Avoid unnecessary generic questions.
- Avoid duplicate questions.
- Avoid repeated scenarios.
- Avoid asking the same skill twice in the same way.
- Be professionally written.
- Be easy for a candidate to understand.

DO NOT generate:

- "Tell me about yourself"
- "What are your strengths?"
- "What are your weaknesses?"
- generic questions unrelated to the position

unless they are specifically useful for the position.

Do not include:

- correct answers
- scores
- evaluations
- explanations
- recruiter notes
- Markdown


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
            "options": [
                "Excellent",
                "Good",
                "Average",
                "Poor",
                "Very Poor"
            ]
        }},
        {{
            "question": "",
            "type": "short_answer"
        }}
    ]
}}

FINAL REQUIREMENTS:

- EXACTLY 10 questions.
- 3 mcq.
- 2 situational_mcq.
- 2 yes_no.
- 2 rating.
- 1 short_answer.
- Every question must be different.
- No question may duplicate the previous questions.
- Return COMPLETE JSON.
"""

    result = ask_ai(prompt)

    if not isinstance(result, dict):
        raise ValueError(
            "Interview question generation returned invalid data."
        )

    questions = result.get(
        "questions",
        []
    )

    if not isinstance(
        questions,
        list
    ):
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

        if not isinstance(
            item,
            dict
        ):
            continue

        question = str(
            item.get(
                "question",
                ""
            )
        ).strip()

        question_type = str(
            item.get(
                "type",
                ""
            )
        ).strip().lower()

        if not question:
            continue

        if question_type not in allowed_types:
            continue

        # --------------------------------------------------
        # MCQ
        # --------------------------------------------------

        if question_type in {
            "mcq",
            "situational_mcq"
        }:

            options = item.get(
                "options",
                []
            )

            if not isinstance(
                options,
                list
            ):
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

        # --------------------------------------------------
        # YES / NO
        # --------------------------------------------------

        elif question_type == "yes_no":

            clean_questions.append({
                "question": question,
                "type": "yes_no",
                "options": [
                    "Yes",
                    "No"
                ]
            })

        # --------------------------------------------------
        # RATING
        # --------------------------------------------------

        elif question_type == "rating":

            clean_questions.append({
                "question": question,
                "type": "rating",
                "options": [
                    "Excellent",
                    "Good",
                    "Average",
                    "Poor",
                    "Very Poor"
                ]
            })

        # --------------------------------------------------
        # SHORT ANSWER
        # --------------------------------------------------

        elif question_type == "short_answer":

            clean_questions.append({
                "question": question,
                "type": "short_answer"
            })

    # ======================================================
    # REMOVE DUPLICATE QUESTIONS
    # ======================================================

    unique_questions = []
    seen_questions = set()

    for item in clean_questions:

        normalized = (
            item["question"]
            .strip()
            .lower()
        )

        if normalized in seen_questions:
            continue

        # Do not allow exact previous question
        if normalized in {
            q.lower()
            for q in previous_question_text
        }:
            continue

        seen_questions.add(
            normalized
        )

        unique_questions.append(
            item
        )

    # ======================================================
    # VALIDATE QUESTION DISTRIBUTION
    # ======================================================

    mcq_count = sum(
        1
        for q in unique_questions
        if q["type"] == "mcq"
    )

    situational_count = sum(
        1
        for q in unique_questions
        if q["type"] == "situational_mcq"
    )

    yes_no_count = sum(
        1
        for q in unique_questions
        if q["type"] == "yes_no"
    )

    rating_count = sum(
        1
        for q in unique_questions
        if q["type"] == "rating"
    )

    short_answer_count = sum(
        1
        for q in unique_questions
        if q["type"] == "short_answer"
    )

    if len(unique_questions) < 10:

        raise ValueError(
            f"AI generated only "
            f"{len(unique_questions)} unique valid questions. "
            f"Expected exactly 10."
        )

    if mcq_count < 3:
        raise ValueError(
            "Interview must contain at least 3 MCQ questions."
        )

    if situational_count < 2:
        raise ValueError(
            "Interview must contain at least 2 situational MCQ questions."
        )

    if yes_no_count < 2:
        raise ValueError(
            "Interview must contain at least 2 Yes/No questions."
        )

    if rating_count < 2:
        raise ValueError(
            "Interview must contain at least 2 rating questions."
        )

    if short_answer_count < 1:
        raise ValueError(
            "Interview must contain at least 1 short-answer question."
        )

    return {
        "questions": unique_questions[:10]
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

    options = options or []

    prompt = f"""
Evaluate the candidate's answer to the interview question.

QUESTION:
{question}

QUESTION TYPE:
{question_type}

OPTIONS:
{json.dumps(
    options,
    ensure_ascii=False
)}

CANDIDATE ANSWER:
{answer}


==========================================================
EVALUATION RULES
==========================================================

Evaluate the answer fairly and professionally.


MCQ / SITUATIONAL MCQ:

- Check whether the selected answer is the best option.
- Use the question and all provided options.
- Give a higher score when the candidate selects the best
  professional response.


YES / NO:

- Do NOT automatically treat Yes as correct.
- Do NOT automatically treat No as wrong.
- Evaluate whether the response is relevant.
- This generally represents candidate experience/background.


RATING:

The candidate selects one of:

- Excellent
- Good
- Average
- Poor
- Very Poor

Convert the rating to a score out of 10:

Excellent = 10
Good = 8
Average = 6
Poor = 4
Very Poor = 2

Do not mark the candidate wrong because it is a
self-assessment.


SHORT ANSWER:

Evaluate:

- relevance
- clarity
- practical understanding
- completeness
- position relevance


==========================================================
SCORING
==========================================================

Return an integer score from 0 to 10.

9-10 = Excellent
7-8  = Good
5-6  = Average
3-4  = Weak
0-2  = Very poor / irrelevant

Do not give everyone the same score.


==========================================================
FEEDBACK
==========================================================

Provide concise professional recruiter feedback.

Mention:

- what was good or bad
- relevance
- what can be improved

Keep it within 2-3 sentences.


==========================================================
RETURN FORMAT
==========================================================

Return ONLY valid JSON:

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

    if not isinstance(
        result,
        dict
    ):
        raise ValueError(
            "Interview answer evaluation returned invalid data."
        )

    try:

        score = int(
            float(
                result.get(
                    "score",
                    0
                )
            )
        )

    except (
        ValueError,
        TypeError
    ):

        score = 0

    score = max(
        0,
        min(10, score)
    )

    evaluation = result.get(
        "evaluation",
        "No evaluation was provided."
    )

    if not isinstance(
        evaluation,
        str
    ):
        evaluation = str(
            evaluation
        )

    evaluation = evaluation.strip()

    if not evaluation:
        evaluation = (
            "No evaluation was provided."
        )

    return {
        "score": score,
        "evaluation": evaluation
    }