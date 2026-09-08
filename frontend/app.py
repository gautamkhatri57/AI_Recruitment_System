import streamlit as st
import requests


BACKEND_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="AI Recruitment System",
    page_icon="👨‍💼",
    layout="wide"
)


if "selected_position" not in st.session_state:
    st.session_state.selected_position = None

if "job_data" not in st.session_state:
    st.session_state.job_data = None

if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None


if "questions" not in st.session_state:
    st.session_state.questions = None


st.title("🤖 AI Recruitment System")
st.write("AI-powered Resume Analysis & Interview System")

st.divider()


try:

    response = requests.get(
        f"{BACKEND_URL}/positions",
        timeout=30
    )

    if response.status_code != 200:
        st.error(
            f"Backend is running but /positions failed:\n{response.text}"
        )
        st.stop()

    positions = response.json().get(
        "positions",
        []
    )

except requests.exceptions.ConnectionError:

    st.error(
        "❌ Backend is not running.\n\n"
        "Start FastAPI using:\n"
        "`uvicorn app.main:app --reload`"
    )

    st.stop()

except requests.exceptions.Timeout:

    st.error(
        "❌ Backend connection timed out."
    )

    st.stop()

except Exception as e:

    st.error(
        f"Backend connection error: {e}"
    )

    st.stop()


st.header("1️⃣ Select Position")


selected_position = st.selectbox(
    "Choose the position you are applying for:",
    positions
)


if selected_position:

    if (
        st.session_state.selected_position
        != selected_position
    ):

        st.session_state.selected_position = selected_position
        st.session_state.job_data = None
        st.session_state.analysis_data = None
        st.session_state.questions = None


    if st.session_state.job_data is None:

        with st.spinner(
            "Loading job requirements..."
        ):

            try:

                response = requests.get(
                    f"{BACKEND_URL}/job",
                    params={
                        "position": selected_position
                    },
                    timeout=120
                )

                if response.status_code != 200:

                    st.error(
                        f"Failed to load JD:\n{response.text}"
                    )

                    st.stop()

                st.session_state.job_data = (
                    response.json()
                )

            except requests.exceptions.Timeout:

                st.error(
                    "JD analysis timed out."
                )

                st.stop()

            except Exception as e:

                st.error(
                    f"Error loading JD: {e}"
                )

                st.stop()


job_data = st.session_state.job_data


if job_data:

    requirements = job_data.get(
        "job_requirements",
        {}
    )

    st.header("2️⃣ Job Requirements")


    col1, col2 = st.columns(2)


    with col1:

        st.subheader("🎯 Required Skills")

        skills = requirements.get(
            "required_skills",
            []
        )

        if skills:

            for skill in skills:
                st.markdown(
                    f"- {skill}"
                )

        else:

            st.info(
                "No specific skills found."
            )


    with col2:

        st.subheader("🎓 Qualification")

        qualification = requirements.get(
            "qualification",
            ""
        )

        st.write(
            qualification
            if qualification
            else "Not specified"
        )


        st.subheader("💼 Experience")

        experience = requirements.get(
            "experience",
            ""
        )

        st.write(
            experience
            if experience
            else "Not specified"
        )


    st.subheader("📋 Job Responsibilities")

    responsibilities = requirements.get(
        "responsibilities",
        []
    )

    if responsibilities:

        for responsibility in responsibilities:

            st.markdown(
                f"- {responsibility}"
            )

    else:

        st.info(
            "No responsibilities found."
        )


st.divider()


st.header("3️⃣ Upload Candidate Resume")


uploaded_file = st.file_uploader(
    "Upload Resume",
    type=["pdf", "docx"],
    help="Upload candidate resume in PDF or DOCX format."
)


if uploaded_file:

    if st.button(
        "🚀 Analyze Resume",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "AI is analyzing the resume against the selected JD..."
        ):

            try:

                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type
                    )
                }

                data = {
                    "position": selected_position
                }


                response = requests.post(
                    f"{BACKEND_URL}/resume/analyze",
                    files=files,
                    data=data,
                    timeout=180
                )


                if response.status_code != 200:

                    st.error(
                        f"Resume analysis failed:\n"
                        f"{response.text}"
                    )

                else:

                    result = response.json()

                    st.session_state.analysis_data = result

                    st.session_state.questions = (
                        result.get(
                            "interview_questions",
                            None
                        )
                    )

                    st.success(
                        "✅ Resume analyzed successfully!"
                    )


            except requests.exceptions.Timeout:

                st.error(
                    "❌ Request timed out. "
                    "AI analysis is taking too long."
                )


            except requests.exceptions.ConnectionError:

                st.error(
                    "❌ Could not connect to backend."
                )


            except Exception as e:

                st.error(
                    f"Error analyzing resume: {e}"
                )


result = st.session_state.analysis_data


if result:

    analysis = result.get(
        "analysis",
        {}
    )


    st.divider()

    st.header("4️⃣ Candidate Analysis")


    st.subheader("👤 Candidate Information")


    col1, col2, col3 = st.columns(3)


    with col1:

        st.write("**Name**")

        st.write(
            analysis.get(
                "candidate_name",
                "Not available"
            )
        )


    with col2:

        st.write("**Email**")

        st.write(
            analysis.get(
                "email",
                "Not available"
            )
        )


    with col3:

        st.write("**Phone**")

        st.write(
            analysis.get(
                "phone",
                "Not available"
            )
        )


    st.subheader("📊 ATS Score")


    score = analysis.get(
        "ats_score",
        0
    )


    score_col1, score_col2 = st.columns(
        [1, 3]
    )


    with score_col1:

        st.metric(
            "ATS Score",
            f"{score}/100"
        )


    with score_col2:

        st.progress(
            min(
                max(
                    int(score),
                    0
                ),
                100
            ) / 100
        )


    st.subheader("🎓 Education")


    education = analysis.get(
        "education",
        []
    )


    if education:

        for item in education:

            if isinstance(item, dict):

                degree = item.get(
                    "degree",
                    item.get(
                        "qualification",
                        ""
                    )
                )

                institution = item.get(
                    "institution",
                    ""
                )

                years = item.get(
                    "years",
                    ""
                )

                status = item.get(
                    "status",
                    ""
                )


                st.markdown(
                    f"**{degree}**  \n"
                    f"{institution}  \n"
                    f"{years}  \n"
                    f"{status}"
                )

                st.divider()

            else:

                st.write(item)

    else:

        st.info(
            "No education information found."
        )


    skill_col1, skill_col2 = st.columns(2)


    with skill_col1:

        st.subheader("✅ Matched Skills")

        matched = analysis.get(
            "matched_skills",
            []
        )


        if matched:

            for skill in matched:

                st.success(
                    skill
                )

        else:

            st.info(
                "No matched skills."
            )


    with skill_col2:

        st.subheader("❌ Missing Skills")

        missing = analysis.get(
            "missing_skills",
            []
        )


        if missing:

            for skill in missing:

                st.error(
                    skill
                )

        else:

            st.success(
                "No missing skills."
            )


    st.subheader("🛠️ Resume Skills")


    resume_skills = analysis.get(
        "resume_skills",
        []
    )


    if resume_skills:

        st.write(
            " • ".join(
                str(skill)
                for skill in resume_skills
            )
        )

    else:

        st.info(
            "No skills found."
        )


    st.subheader("💼 Experience")


    experience = analysis.get(
        "experience",
        []
    )


    if experience:

        for exp in experience:

            if isinstance(exp, dict):

                title = exp.get(
                    "title",
                    ""
                )

                organization = exp.get(
                    "organization",
                    exp.get(
                        "company",
                        ""
                    )
                )

                duration = exp.get(
                    "duration",
                    ""
                )

                location = exp.get(
                    "location",
                    ""
                )


                if title:

                    st.markdown(
                        f"### {title}"
                    )


                if organization:

                    st.write(
                        f"**Organization:** {organization}"
                    )


                if duration:

                    st.write(
                        f"**Duration:** {duration}"
                    )


                if location:

                    st.write(
                        f"**Location:** {location}"
                    )


                exp_responsibilities = exp.get(
                    "responsibilities",
                    []
                )


                for responsibility in exp_responsibilities:

                    st.markdown(
                        f"- {responsibility}"
                    )

            else:

                st.write(exp)

    else:

        st.info(
            "No experience found."
        )


    st.subheader("📁 Projects")


    projects = analysis.get(
        "projects",
        []
    )


    if projects:

        for project in projects:

            if isinstance(project, dict):

                name = project.get(
                    "name",
                    project.get(
                        "title",
                        ""
                    )
                )

                description = project.get(
                    "description",
                    ""
                )

                if name:

                    st.markdown(
                        f"**{name}**"
                    )

                if description:

                    st.write(
                        description
                    )

            else:

                st.markdown(
                    f"- {project}"
                )

    else:

        st.info(
            "No projects found."
        )


    st.subheader("🏆 Certifications")


    certifications = analysis.get(
        "certifications",
        []
    )


    if certifications:

        for certification in certifications:

            st.markdown(
                f"- {certification}"
            )

    else:

        st.info(
            "No certifications found."
        )


    st.subheader("🎯 Eligibility Match")


    match_col1, match_col2 = st.columns(2)


    with match_col1:

        if analysis.get(
            "qualification_match",
            False
        ):

            st.success(
                "✅ Qualification Match"
            )

        else:

            st.error(
                "❌ Qualification Does Not Match"
            )


    with match_col2:

        if analysis.get(
            "experience_match",
            False
        ):

            st.success(
                "✅ Experience Match"
            )

        else:

            st.warning(
                "⚠️ Experience Does Not Match"
            )


    st.subheader("🧑‍💼 Recruiter Recommendation")


    recommendation = analysis.get(
        "recommendation",
        ""
    )


    st.info(
        recommendation
        if recommendation
        else "No recommendation available."
    )


if result:

    st.divider()

    st.header("5️⃣ AI Interview Questions")

    st.write(
        "Personalized interview questions generated "
        "from the selected position, JD and candidate resume."
    )


    questions_data = st.session_state.questions


    if questions_data:

        questions = questions_data.get(
            "questions",
            []
        )


        if questions:

            for index, item in enumerate(
                questions,
                start=1
            ):

                if isinstance(item, dict):

                    question = item.get(
                        "question",
                        ""
                    )

                    category = item.get(
                        "category",
                        "Interview"
                    )


                    with st.expander(
                        f"Question {index}: {category}"
                    ):

                        st.write(
                            question
                        )

                else:

                    with st.expander(
                        f"Question {index}"
                    ):

                        st.write(
                            item
                        )

        else:

            st.info(
                "No interview questions generated."
            )

    else:

        st.info(
            "Interview questions are not available."
        )


st.divider()


st.caption(
    "AI Recruitment System • "
    "FastAPI + Streamlit + Groq AI"
)

