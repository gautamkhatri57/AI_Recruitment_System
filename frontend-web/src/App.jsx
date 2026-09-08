import { useEffect, useState } from "react";
import "./App.css";

const BACKEND_URL = "http://127.0.0.1:8000";

function App() {
  const [positions, setPositions] = useState([]);
  const [loadingPositions, setLoadingPositions] = useState(true);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    position: "",
    positionId: "",
    resume: null,
  });

  const [applicationId, setApplicationId] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(1);

  const [loading, setLoading] = useState(false);
  const [submittingInterview, setSubmittingInterview] = useState(false);
  const [error, setError] = useState("");

  const [resumeScore, setResumeScore] = useState(null);
  const [interviewScore, setInterviewScore] = useState(null);
  const [overallScore, setOverallScore] = useState(null);
  const [finalRecommendation, setFinalRecommendation] = useState("");

  const formatBackendError = (data) => {
    if (!data) return "Something went wrong.";

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item?.msg) return item.msg;
          return JSON.stringify(item);
        })
        .join(", ");
    }

    if (data.detail && typeof data.detail === "object") {
      return data.detail.msg || JSON.stringify(data.detail);
    }

    if (typeof data.message === "string") {
      return data.message;
    }

    return "Something went wrong.";
  };

  useEffect(() => {
    const loadPositions = async () => {
      try {
        setLoadingPositions(true);
        setError("");

        const response = await fetch(`${BACKEND_URL}/positions`);
        const data = await response.json();

        console.log("Positions API response:", data);

        if (!response.ok) {
          throw new Error(formatBackendError(data));
        }

        const loadedPositions = Array.isArray(data.positions)
          ? data.positions
          : [];

        setPositions(loadedPositions);
      } catch (error) {
        console.error("Position loading error:", error);

        setError(
          error.message || "Could not load job positions."
        );
      } finally {
        setLoadingPositions(false);
      }
    };

    loadPositions();
  }, []);

  const handleChange = (e) => {
    const { name, value, files } = e.target;

    if (name === "position") {
      const selectedPosition = positions.find(
        (position) =>
          String(position.id) === String(value)
      );

      setFormData((previous) => ({
        ...previous,
        position: selectedPosition
          ? selectedPosition.title
          : "",
        positionId: selectedPosition
          ? String(selectedPosition.id)
          : "",
      }));

      setError("");
      return;
    }

    setFormData((previous) => ({
      ...previous,
      [name]: files ? files[0] : value,
    }));

    if (error) {
      setError("");
    }
  };

  const handleApplicationSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.name.trim()) {
      setError("Please enter your name.");
      return;
    }

    if (!formData.email.trim()) {
      setError("Please enter your email.");
      return;
    }

    if (!formData.phone.trim()) {
      setError("Please enter your phone number.");
      return;
    }

    if (!formData.positionId) {
      setError("Please select a position.");
      return;
    }

    if (!formData.resume) {
      setError("Please upload your resume.");
      return;
    }

    const fileName = formData.resume.name.toLowerCase();

    if (
      !fileName.endsWith(".pdf") &&
      !fileName.endsWith(".docx")
    ) {
      setError("Only PDF and DOCX resumes are allowed.");
      return;
    }

    if (formData.resume.size > 5 * 1024 * 1024) {
      setError("Resume size should not exceed 5 MB.");
      return;
    }

    setLoading(true);

    const form = new FormData();

    form.append("name", formData.name.trim());
    form.append("email", formData.email.trim());
    form.append("phone", formData.phone.trim());
    form.append("position", formData.position);
    form.append("position_id", formData.positionId);
    form.append("file", formData.resume);

    console.log("Submitting application:", {
      name: formData.name,
      email: formData.email,
      phone: formData.phone,
      position: formData.position,
      position_id: formData.positionId,
      resume: formData.resume.name,
    });

    try {
      const response = await fetch(
        `${BACKEND_URL}/resume/analyze`,
        {
          method: "POST",
          body: form,
        }
      );

      const result = await response.json();

      console.log("Backend response:", result);

      if (!response.ok) {
        throw new Error(formatBackendError(result));
      }

      if (!result.application_id) {
        throw new Error(
          "Application ID was not returned by backend."
        );
      }

      setApplicationId(result.application_id);

      if (result.resume_score !== undefined) {
        setResumeScore(result.resume_score);
      } else if (result.ats_score !== undefined) {
        setResumeScore(result.ats_score);
      } else if (result.analysis?.score !== undefined) {
        setResumeScore(result.analysis.score);
      }

      const generatedQuestions =
        result.interview_questions?.questions || [];

      console.log(
        "Generated interview questions:",
        generatedQuestions
      );

      if (
        !Array.isArray(generatedQuestions) ||
        generatedQuestions.length === 0
      ) {
        throw new Error(
          "Application was processed, but no interview questions were generated."
        );
      }

      setQuestions(generatedQuestions);

      const initialAnswers = {};

      generatedQuestions.forEach((question, index) => {
        const questionId = question.id ?? index;
        initialAnswers[questionId] = "";
      });

      setAnswers(initialAnswers);
      setStep(2);
    } catch (error) {
      console.error("Application error:", error);

      setError(
        error.message ||
          "Unable to process your application."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers((previous) => ({
      ...previous,
      [questionId]: value,
    }));

    if (error) {
      setError("");
    }
  };

  const handleInterviewSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!applicationId) {
      setError(
        "Application information is missing. Please start again."
      );
      return;
    }

    for (let i = 0; i < questions.length; i++) {
      const question = questions[i];
      const questionId = question.id ?? i;
      const answer = answers[questionId];

      if (
        answer === undefined ||
        answer === null ||
        String(answer).trim() === ""
      ) {
        setError(
          `Please answer question ${i + 1} before submitting.`
        );
        return;
      }
    }

    const answerPayload = questions.map(
      (question, index) => {
        const questionId = question.id ?? index;

        return {
          question_id: questionId,
          answer: answers[questionId] ?? "",
        };
      }
    );

    const payload = {
      application_id: applicationId,
      answers: answerPayload,
    };

    console.log(
      "Submitting interview payload:",
      payload
    );

    setSubmittingInterview(true);

    try {
      const response = await fetch(
        `${BACKEND_URL}/interview/submit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const result = await response.json();

      console.log(
        "Interview submit response:",
        result
      );

      if (!response.ok) {
        throw new Error(formatBackendError(result));
      }

      if (
        !result.answers_saved ||
        result.answers_saved <= 0
      ) {
        throw new Error(
          "Interview submission failed. No answers were saved."
        );
      }

      console.log(
        `Successfully saved ${result.answers_saved} answers.`
      );

      setResumeScore(
        result.resume_score ?? resumeScore
      );

      setInterviewScore(
        result.interview_score ?? null
      );

      setOverallScore(
        result.overall_score ?? null
      );

      setFinalRecommendation(
        result.final_recommendation || ""
      );

      console.log("FINAL SCORES:", {
        resume_score: result.resume_score,
        interview_score: result.interview_score,
        overall_score: result.overall_score,
        final_recommendation:
          result.final_recommendation,
      });

      setStep(3);
    } catch (error) {
      console.error(
        "Interview submission error:",
        error
      );

      setError(
        error.message ||
          "Unable to submit interview."
      );
    } finally {
      setSubmittingInterview(false);
    }
  };

  const renderQuestionInput = (item, index) => {
    const questionId = item.id ?? index;

    const type = (
      item.type || "short_answer"
    )
      .toLowerCase()
      .trim();

    if (
      type === "mcq" ||
      type === "situational_mcq"
    ) {
      return (
        <div className="answer-options">
          {(item.options || []).map(
            (option, optionIndex) => (
              <label
                className={`option-item ${
                  answers[questionId] === option
                    ? "selected"
                    : ""
                }`}
                key={optionIndex}
              >
                <input
                  type="radio"
                  name={`question-${questionId}`}
                  value={option}
                  checked={
                    answers[questionId] === option
                  }
                  onChange={(e) =>
                    handleAnswerChange(
                      questionId,
                      e.target.value
                    )
                  }
                />

                <span className="option-radio">
                  {String.fromCharCode(
                    65 + optionIndex
                  )}
                </span>

                <span className="option-text">
                  {option}
                </span>
              </label>
            )
          )}
        </div>
      );
    }

    if (type === "yes_no") {
      return (
        <div className="yes-no-options">
          <label
            className={`yes-no-option ${
              answers[questionId] === "Yes"
                ? "selected"
                : ""
            }`}
          >
            <input
              type="radio"
              name={`question-${questionId}`}
              value="Yes"
              checked={
                answers[questionId] === "Yes"
              }
              onChange={(e) =>
                handleAnswerChange(
                  questionId,
                  e.target.value
                )
              }
            />

            <span>Yes</span>
          </label>

          <label
            className={`yes-no-option ${
              answers[questionId] === "No"
                ? "selected"
                : ""
            }`}
          >
            <input
              type="radio"
              name={`question-${questionId}`}
              value="No"
              checked={
                answers[questionId] === "No"
              }
              onChange={(e) =>
                handleAnswerChange(
                  questionId,
                  e.target.value
                )
              }
            />

            <span>No</span>
          </label>
        </div>
      );
    }

    if (type === "rating") {
      const ratingLabels = {
        1: "Very Poor",
        2: "Poor",
        3: "Average",
        4: "Good",
        5: "Excellent",
      };

      return (
        <div className="rating-container">
          <div className="rating-options">
            {Object.entries(
              ratingLabels
            ).map(([value, label]) => (
              <button
                type="button"
                key={value}
                className={`rating-button ${
                  Number(
                    answers[questionId]
                  ) === Number(value)
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  handleAnswerChange(
                    questionId,
                    value
                  )
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      );
    }

    return (
      <textarea
        className="answer-textarea"
        value={answers[questionId] || ""}
        onChange={(e) =>
          handleAnswerChange(
            questionId,
            e.target.value
          )
        }
        placeholder="Write your answer here..."
        rows="6"
        required
      />
    );
  };

  const getScoreClass = (score) => {
    if (
      score === null ||
      score === undefined
    ) {
      return "";
    }

    const numericScore = Number(score);

    if (numericScore >= 80) {
      return "score-excellent";
    }

    if (numericScore >= 65) {
      return "score-good";
    }

    if (numericScore >= 50) {
      return "score-average";
    }

    return "score-low";
  };

  return (
    <div className="app">

      {/* NAVBAR */}
      <header className="navbar">
        <div className="logo">
          <span className="logo-copy">
            COPYHART
          </span>

          <small>
            Services Private Limited
          </small>
        </div>

        <button
          type="button"
          className="get-started-button"
          onClick={() => {
            document
              .getElementById("application")
              ?.scrollIntoView({
                behavior: "smooth",
              });
          }}
        >
          Get Started
        </button>
      </header>

      <main className="main-container">

        {/* STEP 1 */}
        {step === 1 && (
          <>
            <section
              className="hero-section"
              id="home"
            >
              <div className="hero-content">
                <p className="badge">
                  CAREERS AT COPYHART
                </p>

                <h1>
                  Build Your
                  <br />
                  <span>
                    Future With Us.
                  </span>
                </h1>

                <p className="hero-text">
                  Join CopyHart and
                  become part of a
                  growing team
                  dedicated to
                  delivering
                  professional
                  business and
                  compliance
                  solutions.
                </p>

                <button
                  type="button"
                  className="hero-button"
                  onClick={() => {
                    document
                      .getElementById(
                        "application"
                      )
                      ?.scrollIntoView({
                        behavior:
                          "smooth",
                      });
                  }}
                >
                  Apply Now
                  <span>→</span>
                </button>
              </div>

              {/* CAREER IMAGE */}
              <div className="hero-side">
                <div className="hero-image-wrapper">
                  <img
                    src="/career-hero.jpeg"
                    alt="Build Your Career at CopyHart"
                    className="hero-career-image"
                  />
                </div>
              </div>
            </section>

            <section className="company-highlights">
              <div>
                <strong>18+</strong>
                <span>
                  Years of Excellence
                </span>
              </div>

              <div>
                <strong>36000+</strong>
                <span>
                  Active Files
                </span>
              </div>

              <div>
                <strong>30+</strong>
                <span>
                  Professionals
                </span>
              </div>

              <div>
                <strong>Pan-India</strong>
                <span>
                  Presence
                </span>
              </div>
            </section>

            <section
              className="application-card"
              id="application"
            >
              <div className="card-header">
                <p className="section-label">
                  CAREER OPPORTUNITY
                </p>

                <h2>
                  Job Application
                </h2>

                <p>
                  Please provide your
                  details and upload
                  your latest resume
                  to apply for an
                  available position
                  at CopyHart.
                </p>
              </div>

              <form
                onSubmit={
                  handleApplicationSubmit
                }
              >
                <div className="form-grid">

                  <div className="form-group">
                    <label>
                      Full Name
                    </label>

                    <input
                      type="text"
                      name="name"
                      placeholder="Enter your full name"
                      value={formData.name}
                      onChange={
                        handleChange
                      }
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>
                      Email Address
                    </label>

                    <input
                      type="email"
                      name="email"
                      placeholder="Enter your email"
                      value={formData.email}
                      onChange={
                        handleChange
                      }
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>
                      Phone Number
                    </label>

                    <input
                      type="tel"
                      name="phone"
                      placeholder="Enter your phone number"
                      value={formData.phone}
                      onChange={
                        handleChange
                      }
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>
                      Position
                    </label>

                    <div className="select-wrapper">
                      <select
                        name="position"
                        className="position-select"
                        value={
                          formData.positionId
                        }
                        onChange={
                          handleChange
                        }
                        disabled={
                          loadingPositions
                        }
                        required
                      >
                        <option value="">
                          {loadingPositions
                            ? "Loading positions..."
                            : positions.length ===
                              0
                            ? "No positions available"
                            : "Select a position"}
                        </option>

                        {positions.map(
                          (position) => (
                            <option
                              key={
                                position.id
                              }
                              value={
                                position.id
                              }
                            >
                              {
                                position.title
                              }
                            </option>
                          )
                        )}
                      </select>
                    </div>

                    {formData.positionId && (
                      <div className="selected-position-info">
                        <strong>
                          Selected Position
                        </strong>

                        <span>
                          {
                            formData.position
                          }
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="form-group resume-group">
                  <label>
                    Resume
                  </label>

                  <div className="upload-box">
                    <input
                      type="file"
                      name="resume"
                      accept=".pdf,.docx"
                      onChange={
                        handleChange
                      }
                      required
                    />

                    <div className="upload-content">
                      <div className="upload-icon">
                        ↑
                      </div>

                      <strong>
                        {formData.resume
                          ? formData.resume.name
                          : "Upload your resume"}
                      </strong>

                      <span>
                        PDF or DOCX •
                        Maximum
                        recommended
                        size 5 MB
                      </span>
                    </div>
                  </div>
                </div>

                {error && (
                  <div className="error-message">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="submit-button"
                  disabled={
                    loading ||
                    loadingPositions ||
                    positions.length === 0
                  }
                >
                  {loading
                    ? "Processing Application..."
                    : "Continue to Interview"}

                  {!loading && (
                    <span>→</span>
                  )}
                </button>
              </form>
            </section>
          </>
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <section className="interview-section">

            <div className="interview-header">
              <p className="badge">
                CANDIDATE INTERVIEW
              </p>

              <h1>
                Interview Questions
              </h1>

              <p className="hero-text">
                Please answer the
                following questions
                to complete your
                application.
              </p>

              <div className="candidate-info">
                <div>
                  <strong>
                    Candidate
                  </strong>

                  <span>
                    {formData.name}
                  </span>
                </div>

                <div>
                  <strong>
                    Position
                  </strong>

                  <span>
                    {formData.position}
                  </span>
                </div>
              </div>
            </div>

            <form
              className="questions-form"
              onSubmit={
                handleInterviewSubmit
              }
            >
              {questions.map(
                (item, index) => {
                  const question =
                    typeof item ===
                    "string"
                      ? item
                      : item.question ||
                        item.text ||
                        "";

                  const type =
                    typeof item ===
                    "object"
                      ? (
                          item.type ||
                          "short_answer"
                        )
                          .toLowerCase()
                          .trim()
                      : "short_answer";

                  let typeLabel =
                    "Short Answer";

                  if (type === "mcq") {
                    typeLabel =
                      "Multiple Choice";
                  }

                  if (
                    type ===
                    "situational_mcq"
                  ) {
                    typeLabel =
                      "Situational";
                  }

                  if (
                    type === "yes_no"
                  ) {
                    typeLabel =
                      "Yes / No";
                  }

                  if (
                    type === "rating"
                  ) {
                    typeLabel =
                      "Self Rating";
                  }

                  return (
                    <div
                      className="question-card"
                      key={
                        item.id ??
                        index
                      }
                    >
                      <div className="question-header">
                        <span className="question-number">
                          Question{" "}
                          {index + 1}
                        </span>

                        <span className="question-category">
                          {
                            typeLabel
                          }
                        </span>
                      </div>

                      <h3>
                        {question}
                      </h3>

                      {renderQuestionInput(
                        item,
                        index
                      )}
                    </div>
                  );
                }
              )}

              {error && (
                <div className="error-message">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="submit-button"
                disabled={
                  submittingInterview
                }
              >
                {submittingInterview
                  ? "Submitting Interview..."
                  : "Submit Interview"}

                {!submittingInterview && (
                  <span>→</span>
                )}
              </button>
            </form>
          </section>
        )}

        {/* STEP 3 */}
        {step === 3 && (
          <section className="success-card">

            <div className="success-icon">
              ✓
            </div>

            <p className="section-label">
              APPLICATION COMPLETE
            </p>

            <h1>
              Application Submitted
            </h1>

            <p>
              Your application and
              interview have been
              submitted successfully.
            </p>

            <div className="success-message">
              <p>
                Our recruitment team
                will review your
                application and contact
                you if you are selected
                for the next stage.
              </p>
            </div>

            <p className="success-note">
              Thank you for your
              interest in joining
              CopyHart.
            </p>

          </section>
        )}
      </main>

      <footer>
        <div className="footer-brand">
          <strong>
            COPYHART
          </strong>

          <span>
            Services Private Limited
          </span>
        </div>

        <p>
          Business Registration &
          Compliance Services
        </p>
      </footer>
    </div>
  );
}

export default App;

