import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "https://ai-recruitment-backend-nv6b.onrender.com";

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "-";

  if (Array.isArray(value)) {
    return value
      .map((item) =>
        typeof item === "object"
          ? Object.entries(item)
              .map(([key, val]) => `${formatAnalysisKey(key)}: ${formatValue(val)}`)
              .join(" | ")
          : String(item)
      )
      .filter(Boolean)
      .join(", ");
  }

  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, val]) => `${formatAnalysisKey(key)}: ${formatValue(val)}`)
      .join(" | ");
  }

  return String(value);
}

function parseMaybeJSON(value) {
  if (value === null || value === undefined) return value;
  if (typeof value !== "string") return value;

  let current = value;

  for (let i = 0; i < 3; i++) {
    if (typeof current !== "string") return current;

    let cleaned = current.trim();

    if (!cleaned) return "";

    cleaned = cleaned
      .replace(/^```json\s*/i, "")
      .replace(/^```\s*/, "")
      .replace(/\s*```$/, "")
      .trim();

    try {
      current = JSON.parse(cleaned);
    } catch {
      return current;
    }
  }

  return current;
}

function formatAnalysisKey(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function renderAnalysisValue(value) {
  const parsed = parseMaybeJSON(value);

  if (parsed === null || parsed === undefined || parsed === "") {
    return <span className="analysis-empty">No information available.</span>;
  }

  if (Array.isArray(parsed)) {
    if (parsed.length === 0) {
      return <span className="analysis-empty">No information available.</span>;
    }

    return (
      <ul className="analysis-list">
        {parsed.map((item, index) => (
          <li key={index}>
            {typeof item === "object"
              ? renderAnalysisValue(item)
              : String(item)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof parsed === "object") {
    return (
      <div className="analysis-object">
        {Object.entries(parsed).map(([key, val]) => (
          <div className="analysis-field" key={key}>
            <h4>{formatAnalysisKey(key)}</h4>
            <div className="analysis-field-value">
              {renderAnalysisValue(val)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(parsed)}</span>;
}

function getPositionTitle(candidate) {
  if (!candidate) return "-";

  if (candidate.position_title) return candidate.position_title;

  if (candidate.position) {
    return typeof candidate.position === "object"
      ? candidate.position.title || "-"
      : candidate.position;
  }

  return "-";
}

function getAnalysis(candidate) {
  if (!candidate) return {};

  const raw =
    candidate.analysis ||
    candidate.resume_analysis ||
    {};

  const analysis = parseMaybeJSON(raw);

  if (!analysis || typeof analysis !== "object" || Array.isArray(analysis)) {
    return {};
  }

  return {
    ...analysis,
    strengths: parseMaybeJSON(analysis.strengths),
    weaknesses: parseMaybeJSON(analysis.weaknesses),
    suggestions: parseMaybeJSON(analysis.suggestions),
  };
}

function getResumeScore(candidate) {
  const analysis = getAnalysis(candidate);

  return (
    candidate?.resume_score ??
    candidate?.score ??
    analysis?.score ??
    null
  );
}

function getInterviewScore(candidate) {
  const analysis = getAnalysis(candidate);

  return (
    candidate?.interview_score ??
    analysis?.interview_score ??
    null
  );
}

function getOverallScore(candidate) {
  const analysis = getAnalysis(candidate);

  return (
    candidate?.overall_score ??
    analysis?.overall_score ??
    null
  );
}

function getRecommendation(candidate) {
  const analysis = getAnalysis(candidate);

  return (
    candidate?.final_recommendation ??
    candidate?.recommendation ??
    analysis?.final_recommendation ??
    "-"
  );
}

function getCandidateName(candidate) {
  return (
    candidate?.full_name ||
    candidate?.name ||
    candidate?.candidate?.full_name ||
    "-"
  );
}

function getCandidateEmail(candidate) {
  return (
    candidate?.email ||
    candidate?.candidate?.email ||
    "-"
  );
}

function getCandidatePhone(candidate) {
  return (
    candidate?.phone ||
    candidate?.candidate?.phone ||
    "-"
  );
}

function getResumeFilename(candidate) {
  return (
    candidate?.original_filename ||
    candidate?.resume?.original_filename ||
    "-"
  );
}

function getQuestions(candidate) {
  if (Array.isArray(candidate?.interview?.questions)) {
    return candidate.interview.questions;
  }

  if (Array.isArray(candidate?.interview_questions)) {
    return candidate.interview_questions;
  }

  if (Array.isArray(candidate?.questions)) {
    return candidate.questions;
  }

  return [];
}

function formatApiError(value) {
  if (!value) return "Something went wrong.";

  if (typeof value === "string") return value;

  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === "string") return item;

        const location = Array.isArray(item?.loc)
          ? item.loc.filter(Boolean).join(" → ")
          : "";

        const message =
          item?.msg ||
          item?.message ||
          item?.detail ||
          JSON.stringify(item);

        return location ? `${message} (${location})` : message;
      })
      .join("\n");
  }

  if (typeof value === "object") {
    return (
      value.message ||
      value.msg ||
      value.detail ||
      value.error ||
      JSON.stringify(value)
    );
  }

  return String(value);
}

function App() {
  const [admin, setAdmin] = useState(null);
  const [activePage, setActivePage] = useState("dashboard");

  const [candidates, setCandidates] = useState([]);
  const [positions, setPositions] = useState([]);

  const [selectedCandidate, setSelectedCandidate] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [showPositionForm, setShowPositionForm] = useState(false);
  const [editingPosition, setEditingPosition] = useState(null);

  const [positionForm, setPositionForm] = useState({
    title: "",
    description: "",
    required_skills: "",
    education: "",
    experience_required: "",
    responsibilities: "",
    is_active: true,
  });

  useEffect(() => {
    const savedAdmin = localStorage.getItem("admin_data");
    const token = localStorage.getItem("admin_token");

    if (savedAdmin && token) {
      try {
        setAdmin(JSON.parse(savedAdmin));
      } catch {
        localStorage.removeItem("admin_data");
        localStorage.removeItem("admin_token");
      }
    }
  }, []);

  useEffect(() => {
    if (admin) {
      loadCandidates();
      loadPositions();
    }
  }, [admin]);

  const getHeaders = () => ({
    Accept: "application/json",
    Authorization: `Bearer ${localStorage.getItem("admin_token")}`,
  });

  const handleApiError = async (response) => {
    let message = `Request failed (${response.status}).`;

    try {
      const data = await response.json();

      message = formatApiError(
        data?.detail ||
          data?.message ||
          data?.error ||
          data
      );
    } catch {
      message = "Server returned an invalid response.";
    }

    if (response.status === 401) {
      localStorage.removeItem("admin_token");
      localStorage.removeItem("admin_data");
      setAdmin(null);
    }

    throw new Error(message);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_URL}/admin/logout`, {
        method: "POST",
        headers: getHeaders(),
      });
    } catch {}

    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_data");

    setAdmin(null);
    setCandidates([]);
    setPositions([]);
    setSelectedCandidate(null);
  };

  const loadCandidates = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/admin/candidates`,
        {
          headers: getHeaders(),
        }
      );

      if (!response.ok) {
        await handleApiError(response);
      }

      const data = await response.json();

      setCandidates(
        Array.isArray(data)
          ? data
          : data?.candidates || data?.data || []
      );
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load candidates.");
    } finally {
      setLoading(false);
    }
  };

  const loadPositions = async () => {
    try {
      const response = await fetch(
        `${API_URL}/admin/positions`,
        {
          headers: getHeaders(),
        }
      );

      if (!response.ok) {
        await handleApiError(response);
      }

      const data = await response.json();

      setPositions(
        Array.isArray(data)
          ? data
          : data?.positions || data?.data || []
      );
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load positions.");
    }
  };

  const loadCandidateDetails = async (resumeId) => {
    if (!resumeId) {
      setError("Candidate ID is missing.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/admin/candidates/${resumeId}`,
        {
          headers: getHeaders(),
        }
      );

      if (!response.ok) {
        await handleApiError(response);
      }

      const data = await response.json();

      setSelectedCandidate(data);
    } catch (err) {
      console.error(err);
      setError(
        err.message || "Unable to load candidate details."
      );
    } finally {
      setLoading(false);
    }
  };

  const openAddPosition = () => {
    setEditingPosition(null);

    setPositionForm({
      title: "",
      description: "",
      required_skills: "",
      education: "",
      experience_required: "",
      responsibilities: "",
      is_active: true,
    });

    setShowPositionForm(true);
  };

  const openEditPosition = (position) => {
    setEditingPosition(position);

    setPositionForm({
      title: position.title || "",
      description: position.description || "",
      required_skills: position.required_skills || "",
      education: position.education || "",
      experience_required: position.experience_required || "",
      responsibilities: position.responsibilities || "",
      is_active: position.is_active ?? true,
    });

    setShowPositionForm(true);
  };

  const savePosition = async (e) => {
    e.preventDefault();

    const payload = {
      title: positionForm.title.trim(),
      description: positionForm.description.trim(),
      required_skills: positionForm.required_skills.trim(),
      education: positionForm.education.trim(),
      experience_required:
        positionForm.experience_required.trim() || null,
      responsibilities:
        positionForm.responsibilities.trim(),
      is_active: Boolean(positionForm.is_active),
    };

    if (!payload.title) {
      setError("Position title is required.");
      return;
    }

    if (!payload.description) {
      setError("Job Description is required.");
      return;
    }

    if (!payload.required_skills) {
      setError("Required skills are required.");
      return;
    }

    if (!payload.education) {
      setError("Education requirement is required.");
      return;
    }

    if (!payload.responsibilities) {
      setError("Responsibilities are required.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const url = editingPosition
        ? `${API_URL}/admin/positions/${editingPosition.id}`
        : `${API_URL}/admin/positions`;

      const method = editingPosition ? "PUT" : "POST";

      console.log("Position payload:", payload);

      const response = await fetch(url, {
        method,
        headers: {
          ...getHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        await handleApiError(response);
      }

      await response.json();

      setShowPositionForm(false);
      setEditingPosition(null);

      setPositionForm({
        title: "",
        description: "",
        required_skills: "",
        education: "",
        experience_required: "",
        responsibilities: "",
        is_active: true,
      });

      await loadPositions();
    } catch (err) {
      console.error("SAVE POSITION ERROR:", err);

      setError(
        err.message || "Unable to save job position."
      );
    } finally {
      setLoading(false);
    }
  };

  const deletePosition = async (positionId) => {
    if (!window.confirm("Are you sure you want to delete this position?")) {
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/admin/positions/${positionId}`,
        {
          method: "DELETE",
          headers: getHeaders(),
        }
      );

      if (!response.ok) {
        await handleApiError(response);
      }

      await loadPositions();
    } catch (err) {
      console.error(err);

      setError(
        err.message || "Unable to delete position."
      );
    } finally {
      setLoading(false);
    }
  };

  if (!admin) {
    return <AdminLogin onLogin={setAdmin} />;
  }

  return (
    <div className="admin-layout">

      <aside className="sidebar">

        <div className="sidebar-brand">
          <div className="sidebar-logo">AI</div>

          <div>
            <h2>AI Recruitment</h2>
            <span>Admin Portal</span>
          </div>
        </div>

        <nav className="sidebar-nav">

          <button
            className={
              activePage === "dashboard"
                ? "nav-active"
                : ""
            }
            onClick={() => {
              setActivePage("dashboard");
              setSelectedCandidate(null);
            }}
          >
            📊 Dashboard
          </button>

          <button
            className={
              activePage === "candidates"
                ? "nav-active"
                : ""
            }
            onClick={() => {
              setActivePage("candidates");
              setSelectedCandidate(null);
              loadCandidates();
            }}
          >
            👥 Candidates
          </button>

          <button
            className={
              activePage === "positions"
                ? "nav-active"
                : ""
            }
            onClick={() => {
              setActivePage("positions");
              setSelectedCandidate(null);
              loadPositions();
            }}
          >
            💼 Job Positions
          </button>

        </nav>

        <div className="sidebar-bottom">

          <div className="logged-admin">

            <div className="admin-avatar">
              {admin.full_name?.charAt(0)?.toUpperCase() || "A"}
            </div>

            <div>
              <strong>{admin.full_name}</strong>
              <span>Administrator</span>
            </div>

          </div>

          <button
            className="logout-sidebar"
            onClick={handleLogout}
          >
            🚪 Logout
          </button>

        </div>

      </aside>

      <main className="main-content">

        <header className="topbar">

          <div>
            <h1>
              {activePage === "dashboard" && "Dashboard"}
              {activePage === "candidates" && "Candidates"}
              {activePage === "positions" && "Job Positions"}
            </h1>

            <p>AI Recruitment Management System</p>
          </div>

          <div className="topbar-admin">

            <div className="topbar-avatar">
              {admin.full_name?.charAt(0)?.toUpperCase() || "A"}
            </div>

            <span>{admin.full_name}</span>

          </div>

        </header>

        {error && (
          <div className="global-error">

            <span>{error}</span>

            <button onClick={() => setError("")}>
              ×
            </button>

          </div>
        )}

        {activePage === "dashboard" && (
          <Dashboard
            candidates={candidates}
            positions={positions}
            onCandidateClick={loadCandidateDetails}
            onGoCandidates={() => {
              setActivePage("candidates");
              setSelectedCandidate(null);
            }}
          />
        )}

        {activePage === "candidates" && (
          <CandidatesPage
            candidates={candidates}
            loading={loading}
            selectedCandidate={selectedCandidate}
            onCandidateClick={loadCandidateDetails}
            onBack={() => setSelectedCandidate(null)}
          />
        )}

        {activePage === "positions" && (
          <PositionsPage
            positions={positions}
            loading={loading}
            onAdd={openAddPosition}
            onEdit={openEditPosition}
            onDelete={deletePosition}
          />
        )}

        {showPositionForm && (
          <PositionModal
            editingPosition={editingPosition}
            form={positionForm}
            setForm={setPositionForm}
            onClose={() => setShowPositionForm(false)}
            onSubmit={savePosition}
            loading={loading}
          />
        )}

      </main>

    </div>
  );
}

function AdminLogin({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/admin/login?email=${encodeURIComponent(
          email
        )}&password=${encodeURIComponent(password)}`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          formatApiError(
            data?.detail ||
              data?.message ||
              data?.error
          )
        );
      }

      localStorage.setItem("admin_token", data.token);
      localStorage.setItem(
        "admin_data",
        JSON.stringify(data.admin)
      );

      onLogin(data.admin);
    } catch (err) {
      console.error(err);

      setError(
        err.message || "Login failed."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">

      <div className="login-card">

        <div className="brand">

          <div className="brand-icon">
            AI
          </div>

          <div>
            <h2>AI Recruitment</h2>
            <p>Admin Portal</p>
          </div>

        </div>

        <div className="login-heading">

          <h1>Admin Login</h1>

          <p>
            Sign in to manage candidates
            and job positions.
          </p>

        </div>

        <form onSubmit={handleLogin}>

          <div className="form-group">

            <label>Email Address</label>

            <input
              type="email"
              placeholder="Enter admin email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

          </div>

          <div className="form-group">

            <label>Password</label>

            <input
              type="password"
              placeholder="Enter admin password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-btn"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

        </form>

        <div className="security-note">
          🔒 Authorized admin access only
        </div>

      </div>

    </div>
  );
}

function Dashboard({
  candidates,
  positions,
  onCandidateClick,
  onGoCandidates,
}) {
  const analyzed = candidates.filter(
    (candidate) =>
      getResumeScore(candidate) !== null
  ).length;

  const recommended = candidates.filter(
    (candidate) => {
      const value = getRecommendation(candidate);

      if (!value) return false;

      const text = String(value).toLowerCase();

      return (
        text.includes("recommended") &&
        !text.includes("not recommended")
      );
    }
  ).length;

  return (
    <div className="page-container">

      <section className="stats-grid">

        <StatCard
          icon="👥"
          title="Total Candidates"
          value={candidates.length}
          subtitle="Registered candidates"
        />

        <StatCard
          icon="💼"
          title="Job Positions"
          value={positions.length}
          subtitle="Available positions"
        />

        <StatCard
          icon="📄"
          title="Analyzed Resumes"
          value={analyzed}
          subtitle="Completed analysis"
        />

        <StatCard
          icon="⭐"
          title="Recommended"
          value={recommended}
          subtitle="Recommended candidates"
        />

      </section>

      <section className="content-card">

        <div className="card-header">

          <div>
            <h2>Recent Candidates</h2>
            <p>Latest candidates in the system.</p>
          </div>

          <button
            className="primary-btn"
            onClick={onGoCandidates}
          >
            View All
          </button>

        </div>

        {candidates.length === 0 ? (
          <EmptyState message="No candidates found." />
        ) : (
          <CandidateTable
            candidates={candidates.slice(0, 10)}
            onCandidateClick={onCandidateClick}
          />
        )}

      </section>

    </div>
  );
}

function StatCard({
  icon,
  title,
  value,
  subtitle,
}) {
  return (
    <div className="stat-card">

      <div className="stat-icon">
        {icon}
      </div>

      <div>
        <span>{title}</span>
        <strong>{value}</strong>
        <small>{subtitle}</small>
      </div>

    </div>
  );
}

function CandidatesPage({
  candidates,
  loading,
  selectedCandidate,
  onCandidateClick,
  onBack,
}) {
  if (selectedCandidate) {
    return (
      <CandidateDetails
        candidate={selectedCandidate}
        onBack={onBack}
      />
    );
  }

  return (
    <div className="page-container">

      <section className="content-card">

        <div className="card-header">

          <div>
            <h2>All Candidates</h2>
            <p>
              Candidate information
              and recruitment results.
            </p>
          </div>

          <span className="record-count">
            {candidates.length} Candidates
          </span>

        </div>

        {loading ? (
          <Loading />
        ) : candidates.length === 0 ? (
          <EmptyState message="No candidates found." />
        ) : (
          <CandidateTable
            candidates={candidates}
            onCandidateClick={onCandidateClick}
          />
        )}

      </section>

    </div>
  );
}

function CandidateTable({
  candidates,
  onCandidateClick,
}) {
  return (
    <div className="table-wrapper">

      <table>

        <thead>

          <tr>
            <th>Candidate</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Position</th>
            <th>Resume Score</th>
            <th>Interview Score</th>
            <th>Overall</th>
            <th>Status</th>
            <th>Action</th>
          </tr>

        </thead>

        <tbody>

          {candidates.map((candidate, index) => {

            const id =
              candidate?.resume_id ||
              candidate?.id;

            return (
              <tr
                key={
                  id ||
                  `candidate-${index}`
                }
              >

                <td>
                  <div className="candidate-name">

                    <div className="candidate-avatar">
                      {String(
                        getCandidateName(candidate)
                      )
                        .charAt(0)
                        .toUpperCase()}
                    </div>

                    <strong>
                      {getCandidateName(candidate)}
                    </strong>

                  </div>
                </td>

                <td>
                  {getCandidateEmail(candidate)}
                </td>

                <td>
                  {getCandidatePhone(candidate)}
                </td>

                <td>
                  {getPositionTitle(candidate)}
                </td>

                <td>
                  <ScoreBadge
                    score={getResumeScore(candidate)}
                  />
                </td>

                <td>
                  <ScoreBadge
                    score={getInterviewScore(candidate)}
                  />
                </td>

                <td>
                  <ScoreBadge
                    score={getOverallScore(candidate)}
                  />
                </td>

                <td>
                  <RecommendationBadge
                    value={getRecommendation(candidate)}
                  />
                </td>

                <td>
                  <button
                    className="view-btn"
                    onClick={() =>
                      onCandidateClick(id)
                    }
                  >
                    View
                  </button>
                </td>

              </tr>
            );
          })}

        </tbody>

      </table>

    </div>
  );
}

function CandidateDetails({
  candidate,
  onBack,
}) {
  const position = candidate?.position || {};
  const analysis = getAnalysis(candidate);
  const questions = getQuestions(candidate);

  const resumeScore = getResumeScore(candidate);
  const interviewScore = getInterviewScore(candidate);
  const overallScore = getOverallScore(candidate);
  const recommendation = getRecommendation(candidate);

  return (
    <div className="page-container">

      <button
        className="back-btn"
        onClick={onBack}
      >
        ← Back to Candidates
      </button>

      <div className="candidate-detail-header">

        <div className="large-avatar">
          {String(
            getCandidateName(candidate)
          )
            .charAt(0)
            .toUpperCase()}
        </div>

        <div>

          <h2>
            {getCandidateName(candidate)}
          </h2>

          <p>
            {getCandidateEmail(candidate)}
          </p>

          <span>
            {getCandidatePhone(candidate)}
          </span>

        </div>

      </div>

      <section className="scores-grid">

        <ScoreCard
          title="Resume Score"
          score={resumeScore}
        />

        <ScoreCard
          title="Interview Score"
          score={interviewScore}
        />

        <ScoreCard
          title="Overall Score"
          score={overallScore}
        />

        <div className="recommendation-card">

          <span>Final Recommendation</span>

          <strong>
            {recommendation || "Pending"}
          </strong>

        </div>

      </section>

      <section className="detail-grid">

        <div className="content-card">

          <div className="card-header">
            <div>
              <h2>Candidate Information</h2>
            </div>
          </div>

          <InfoRow
            label="Name"
            value={getCandidateName(candidate)}
          />

          <InfoRow
            label="Email"
            value={getCandidateEmail(candidate)}
          />

          <InfoRow
            label="Phone"
            value={getCandidatePhone(candidate)}
          />

          <InfoRow
            label="Position"
            value={getPositionTitle(candidate)}
          />

          <InfoRow
            label="Resume"
            value={getResumeFilename(candidate)}
          />

        </div>

        <div className="content-card">

          <div className="card-header">

            <div>
              <h2>Job Position</h2>
            </div>

          </div>

          <InfoRow
            label="Position"
            value={position.title}
          />

          <InfoRow
            label="Education"
            value={position.education}
          />

          <InfoRow
            label="Experience"
            value={position.experience_required}
          />

          <div className="analysis-section">

            <h3>Required Skills</h3>

            {renderAnalysisValue(
              position.required_skills
            )}

          </div>

          <div className="analysis-section">

            <h3>Job Description</h3>

            {renderAnalysisValue(
              position.description
            )}

          </div>

          <div className="analysis-section">

            <h3>Responsibilities</h3>

            {renderAnalysisValue(
              position.responsibilities
            )}

          </div>

        </div>

      </section>

      <section className="content-card">

        <div className="card-header">

          <div>

            <h2>Resume Analysis</h2>

            <p>
              AI analysis of the candidate resume.
            </p>

          </div>

        </div>

        <div className="analysis-grid">

          <AnalysisSection
            title="Strengths"
            value={analysis.strengths}
          />

          <AnalysisSection
            title="Weaknesses"
            value={analysis.weaknesses}
          />

        </div>

        <AnalysisSection
          title="Suggestions"
          value={analysis.suggestions}
        />

      </section>

      <section className="content-card">

        <div className="card-header">

          <div>

            <h2>Interview Evaluation</h2>

            <p>
              Questions, answers and AI evaluation.
            </p>

          </div>

          <span className="record-count">
            {questions.length} Questions
          </span>

        </div>

        {questions.length === 0 ? (
          <EmptyState
            message="No interview questions found."
          />
        ) : (
          <div className="questions-list">

            {questions.map((question, index) => {

              const questionText =
                question?.question ||
                question?.question_text ||
                question?.text ||
                "Question unavailable.";

              const answer =
                question?.answer ||
                question?.answers?.[0]?.answer ||
                null;

              const score =
                question?.score ??
                question?.answers?.[0]?.score ??
                null;

              const evaluation =
                question?.evaluation ||
                question?.answers?.[0]?.evaluation ||
                null;

              return (
                <div
                  className="question-card"
                  key={
                    question?.id ||
                    `question-${index}`
                  }
                >

                  <div className="question-top">

                    <span className="question-number">
                      Question {index + 1}
                    </span>

                    <ScoreBadge score={score} />

                  </div>

                  <h3 className="question-text">
                    {String(questionText)}
                  </h3>

                  <div className="answer-box">

                    <label>
                      Candidate Answer
                    </label>

                    <div>
                      {answer
                        ? renderAnalysisValue(answer)
                        : (
                          <span className="analysis-empty">
                            No answer submitted.
                          </span>
                        )}
                    </div>

                  </div>

                  <div className="evaluation-box">

                    <label>
                      AI Evaluation
                    </label>

                    <div>
                      {evaluation
                        ? renderAnalysisValue(evaluation)
                        : (
                          <span className="analysis-empty">
                            No evaluation available.
                          </span>
                        )}
                    </div>

                  </div>

                </div>
              );
            })}

          </div>
        )}

      </section>

      <section className="content-card">

        <div className="card-header">

          <div>

            <h2>Final Recruitment Result</h2>

            <p>
              Overall candidate evaluation.
            </p>

          </div>

        </div>

        <div className="scores-grid">

          <ScoreCard
            title="Resume Score"
            score={resumeScore}
          />

          <ScoreCard
            title="Interview Score"
            score={interviewScore}
          />

          <ScoreCard
            title="Overall Score"
            score={overallScore}
          />

          <div className="recommendation-card">

            <span>
              Final Recommendation
            </span>

            <strong>
              {recommendation || "Pending"}
            </strong>

          </div>

        </div>

      </section>

    </div>
  );
}

function AnalysisSection({
  title,
  value,
}) {
  return (
    <div className="analysis-section">

      <h3>{title}</h3>

      <div className="analysis-content">
        {renderAnalysisValue(value)}
      </div>

    </div>
  );
}

function PositionsPage({
  positions,
  loading,
  onAdd,
  onEdit,
  onDelete,
}) {
  return (
    <div className="page-container">

      <section className="content-card">

        <div className="card-header">

          <div>

            <h2>Job Positions</h2>

            <p>
              Create and manage recruitment positions.
            </p>

          </div>

          <button
            className="primary-btn"
            onClick={onAdd}
          >
            + Add Position
          </button>

        </div>

        {loading ? (
          <Loading />
        ) : positions.length === 0 ? (
          <EmptyState
            message="No job positions found."
          />
        ) : (
          <div className="positions-grid">

            {positions.map((position, index) => (

              <div
                className="position-card"
                key={
                  position.id ||
                  index
                }
              >

                <div className="position-card-top">

                  <div className="position-icon">
                    💼
                  </div>

                  <span
                    className={
                      position.is_active
                        ? "active-status"
                        : "inactive-status"
                    }
                  >
                    {position.is_active
                      ? "Active"
                      : "Inactive"}
                  </span>

                </div>

                <h3>
                  {position.title}
                </h3>

                <p className="position-description">
                  {formatValue(
                    position.description
                  )}
                </p>

                <div className="position-detail">

                  <strong>
                    Education
                  </strong>

                  <p>
                    {formatValue(
                      position.education
                    )}
                  </p>

                </div>

                <div className="position-detail">

                  <strong>
                    Required Skills
                  </strong>

                  <p>
                    {formatValue(
                      position.required_skills
                    )}
                  </p>

                </div>

                <div className="position-detail">

                  <strong>
                    Experience
                  </strong>

                  <p>
                    {formatValue(
                      position.experience_required
                    )}
                  </p>

                </div>

                <div className="position-detail">

                  <strong>
                    Responsibilities
                  </strong>

                  <p>
                    {formatValue(
                      position.responsibilities
                    )}
                  </p>

                </div>

                <div className="position-actions">

                  <button
                    className="edit-btn"
                    onClick={() =>
                      onEdit(position)
                    }
                  >
                    ✏️ Edit
                  </button>

                  <button
                    className="delete-btn"
                    onClick={() =>
                      onDelete(position.id)
                    }
                  >
                    🗑️ Delete
                  </button>

                </div>

              </div>

            ))}

          </div>
        )}

      </section>

    </div>
  );
}

function PositionModal({
  editingPosition,
  form,
  setForm,
  onClose,
  onSubmit,
  loading,
}) {
  const updateField = (field, value) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  return (
    <div className="modal-overlay">

      <div className="modal">

        <div className="modal-header">

          <div>

            <h2>
              {editingPosition
                ? "Edit Job Position"
                : "Add Job Position"}
            </h2>

            <p>
              Define position requirements.
            </p>

          </div>

          <button
            className="modal-close"
            onClick={onClose}
          >
            ×
          </button>

        </div>

        <form onSubmit={onSubmit}>

          <div className="form-group">

            <label>
              Position Title
            </label>

            <input
              type="text"
              placeholder="e.g. AI Developer"
              value={form.title}
              onChange={(e) =>
                updateField(
                  "title",
                  e.target.value
                )
              }
              required
            />

          </div>

          <div className="form-group">

            <label>
              Job Description
            </label>

            <textarea
              placeholder="Enter complete job description..."
              value={form.description}
              onChange={(e) =>
                updateField(
                  "description",
                  e.target.value
                )
              }
              rows="5"
              required
            />

          </div>

          <div className="form-group">

            <label>
              Education Required
            </label>

            <textarea
              placeholder="e.g. BCA, B.Tech, MCA, Computer Science or related field"
              value={form.education}
              onChange={(e) =>
                updateField(
                  "education",
                  e.target.value
                )
              }
              rows="3"
              required
            />

          </div>

          <div className="form-group">

            <label>
              Required Skills
            </label>

            <textarea
              placeholder="Python, SQL, React, FastAPI..."
              value={form.required_skills}
              onChange={(e) =>
                updateField(
                  "required_skills",
                  e.target.value
                )
              }
              rows="3"
              required
            />

          </div>

          <div className="form-group">

            <label>
              Experience Required
            </label>

            <input
              type="text"
              placeholder="e.g. 0-2 years"
              value={form.experience_required}
              onChange={(e) =>
                updateField(
                  "experience_required",
                  e.target.value
                )
              }
            />

          </div>

          <div className="form-group">

            <label>
              Responsibilities
            </label>

            <textarea
              placeholder="Enter key job responsibilities..."
              value={form.responsibilities}
              onChange={(e) =>
                updateField(
                  "responsibilities",
                  e.target.value
                )
              }
              rows="5"
              required
            />

          </div>

          <label className="checkbox-row">

            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) =>
                updateField(
                  "is_active",
                  e.target.checked
                )
              }
            />

            <span>
              Position is active
            </span>

          </label>

          <div className="modal-actions">

            <button
              type="button"
              className="cancel-btn"
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="primary-btn"
              disabled={loading}
            >
              {loading
                ? "Saving..."
                : editingPosition
                ? "Update Position"
                : "Create Position"}
            </button>

          </div>

        </form>

      </div>

    </div>
  );
}

function ScoreCard({
  title,
  score,
}) {
  const exists =
    score !== null &&
    score !== undefined &&
    score !== "";

  return (
    <div className="score-card">

      <span>{title}</span>

      <strong>
        {exists ? score : "-"}
      </strong>

      <small>/ 100</small>

    </div>
  );
}

function ScoreBadge({ score }) {
  if (
    score === null ||
    score === undefined ||
    score === ""
  ) {
    return (
      <span className="score-empty">
        -
      </span>
    );
  }

  const number = Number(score);

  let className = "score-low";

  if (number >= 80) {
    className = "score-high";
  } else if (number >= 60) {
    className = "score-medium";
  }

  return (
    <span
      className={`score-badge ${className}`}
    >
      {score}
    </span>
  );
}

function RecommendationBadge({ value }) {
  if (!value) {
    return (
      <span className="status-pending">
        Pending
      </span>
    );
  }

  const text = String(value);
  const lower = text.toLowerCase();

  const recommended =
    lower.includes("recommended") &&
    !lower.includes("not recommended");

  return (
    <span
      className={
        recommended
          ? "status-recommended"
          : "status-not-recommended"
      }
    >
      {text}
    </span>
  );
}

function InfoRow({
  label,
  value,
}) {
  return (
    <div className="info-row">

      <span>{label}</span>

      <strong>
        {formatValue(value)}
      </strong>

    </div>
  );
}

function Loading() {
  return (
    <div className="loading">

      <div className="spinner"></div>

      <p>Loading...</p>

    </div>
  );
}

function EmptyState({
  message,
}) {
  return (
    <div className="empty-state">

      <div>📭</div>

      <p>{message}</p>

    </div>
  );
}

export default App;