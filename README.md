# AI Recruitment System

An AI-powered recruitment and resume analysis system designed to simplify candidate screening, resume evaluation, interview assessment, and candidate management.

## 🚀 Features

### Candidate Portal

* Candidate registration and login
* Select available job position
* Upload Resume in PDF/DOCX format
* AI-based resume analysis
* Job Description based resume matching
* AI-generated interview questions
* Submit interview answers
* Candidate-friendly application completion flow

### Admin Portal

* Secure Admin Login
* Candidate Management
* View candidate details
* View uploaded resumes
* View resume analysis
* View matched and missing skills
* View strengths and weaknesses
* View interview questions and answers
* AI evaluation of interview answers
* Resume Score
* Interview Score
* Overall Score
* Final Recommendation
* Job Position Management
* Add, Edit and Delete Job Positions
* Manage Job Description, Skills, Education, Experience and Responsibilities

## 📊 Scoring System

### Resume Score

Resume is evaluated against the selected job position and its requirements.

### Interview Score

Individual interview answers are evaluated on a 0–10 scale and converted into a percentage.

### Overall Score

```text
Overall Score =
Resume Score × 60% + Interview Score × 40%
```

### Recommendation

| Score    | Recommendation       |
| -------- | -------------------- |
| 80–100   | Strongly Recommended |
| 65–79    | Recommended          |
| 50–64    | Maybe                |
| Below 50 | Not Recommended      |

## 🛠️ Tech Stack

### Frontend

* React
* Vite
* JavaScript
* CSS

### Backend

* Python
* FastAPI
* SQLAlchemy

### Database

* PostgreSQL

### AI / ML

* Resume text extraction
* NLP-based resume analysis
* AI interview question generation
* AI interview answer evaluation

## 📁 Project Structure

```text
AI_Recruitment_System/
│
├── backend/
│   ├── app/
│   │   ├── analyzer.py
│   │   ├── database.py
│   │   ├── job.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── resume.py
│   │   └── admin.py
│   ├── jobs/
│   └── uploads/
│
├── frontend-web/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   ├── public/
│   └── package.json
│
├── admin-web/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   └── package.json
│
├── .env
├── .gitignore
└── README.md
```

## 💻 Local Setup

### 1. Clone Repository

```bash
git clone https://github.com/gautamkhatri57/AI_Recruitment_System.git
cd AI_Recruitment_System
```

### 2. Backend Setup

Create and activate the Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Configure the PostgreSQL database in `.env`:

```text
DATABASE_URL=your_database_connection_string
```

Start the backend:

```bash
cd backend
source ../.venv/bin/activate
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

## 🎨 Candidate Frontend

Open another terminal:

```bash
cd frontend-web
npm install
npm run dev
```

Candidate Portal:

```text
http://localhost:5174/
```

## 👨‍💼 Admin Frontend

Open another terminal:

```bash
cd admin-web
npm install
npm run dev
```

Admin Portal:

```text
http://localhost:5173/
```

## 🔐 Security

* Passwords are stored as hashes.
* Candidate scores are not displayed on the Candidate Portal.
* Resume and interview scores are accessible only through Admin functionality.
* Environment variables and sensitive configuration are excluded from Git using `.gitignore`.

## 🔄 Application Flow

```text
Candidate
   ↓
Register / Login
   ↓
Select Job Position
   ↓
Upload Resume
   ↓
Resume Analysis
   ↓
Generate Interview Questions
   ↓
Answer Questions
   ↓
Submit Application
   ↓
Admin Reviews Candidate
   ↓
Resume + Interview Evaluation
   ↓
Overall Score
   ↓
Final Recommendation
```

## 📌 Project Status

**Current Status:** Functional prototype / development version

The application currently supports candidate application, resume analysis, interview assessment, administrative candidate management, and job position management.

## 👨‍💻 Author

**Gautam Khatri**

AI Recruitment System — BCA (Artificial Intelligence)
