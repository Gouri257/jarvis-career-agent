# JARVIS — AI Career Agent 🎙

> An AI-powered full-stack career assistant that analyzes resumes against job descriptions, computes ATS compatibility scores, detects skill gaps, and generates personalized project roadmaps — with two-way voice interaction and a live web interface.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=flat-square)](https://jarvis-career-agent.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-Railway-purple?style=flat-square)](https://jarvis-career-agent-production.up.railway.app)
[![GitHub](https://img.shields.io/badge/GitHub-Gouri257-blue?style=flat-square)](https://github.com/Gouri257/jarvis-career-agent)

---

## What is JARVIS?

JARVIS started as a basic voice bot in my 2nd year of college — it could open apps, tell jokes, and search the web. Over time I rebuilt it from scratch into a real AI career assistant that solves an actual problem: helping students figure out exactly what projects to build to get hired.

You paste your resume and a job description. JARVIS tells you:
- Your **ATS compatibility score** (0–100) with matched and missing keywords
- Your **skill gaps** for that specific role
- **Projects to build** with step-by-step guides and tech stacks
- **Existing projects to upgrade** to be more relevant

---

## Live Links

| What | Link |
|---|---|
| Web App | https://jarvis-career-agent.vercel.app |
| Backend API | https://jarvis-career-agent-production.up.railway.app |
| API Docs | https://jarvis-career-agent-production.up.railway.app/docs |
| GitHub | https://github.com/Gouri257/jarvis-career-agent |
| Desktop Release | https://github.com/Gouri257/jarvis-career-agent/releases |

---

## Features

### Core Features
- **ATS Scoring** — TF-IDF vectorization + cosine similarity computes a 0–100 compatibility score between your resume and the job description, with grade (A/B/C/D/F) and keyword breakdown
- **AI Gap Analysis** — Groq AI (Llama 3.3 70B) identifies specific skill gaps and explains why each matters for the role
- **Project Roadmap** — generates 2–3 new project ideas and 1–2 upgrade suggestions, each with tech stack and step-by-step build guide
- **Two-way Voice** — JARVIS listens to voice commands and speaks results aloud (say "analyze", "read first project", "download report", etc.)
- **PDF Export** — downloads a formatted analysis report including ATS score, gaps, and projects

### Backend & Auth
- **User Accounts** — register and login with JWT authentication and bcrypt password hashing
- **Analysis History** — every analysis is saved to PostgreSQL, viewable and reloadable from the History panel
- **REST API** — FastAPI backend with 8 endpoints, auto-documented at `/docs`

### Platforms
- **Web App** — runs in Chrome, deployed on Vercel
- **Python Desktop App** — dark-themed CustomTkinter GUI, runs on Windows

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| Python | Core language |
| FastAPI | REST API framework |
| SQLAlchemy | Database ORM |
| PostgreSQL | Database (hosted on Supabase) |
| JWT (python-jose) | Authentication tokens |
| bcrypt (passlib) | Password hashing |
| scikit-learn | TF-IDF vectorization + cosine similarity |
| numpy | Vector math for ATS scoring |
| Groq API (Llama 3.3 70B) | AI gap analysis and project generation |
| Railway | Backend hosting |
| Supabase | PostgreSQL cloud database |

### Web Frontend
| Technology | Purpose |
|---|---|
| HTML / CSS / JavaScript | UI |
| Web Speech API | Voice input (listen) |
| SpeechSynthesis API | Voice output (speak) |
| jsPDF | PDF report generation |
| Vercel | Frontend hosting |

### Desktop App
| Technology | Purpose |
|---|---|
| Python | Core language |
| CustomTkinter | Dark-themed desktop UI |
| SpeechRecognition | Voice input |
| pyttsx3 | Voice output |
| ReportLab | PDF generation |
| threading | Non-blocking UI during API calls |

---

## Project Structure

```
jarvis-career-agent/
│
├── backend/                    # FastAPI backend
│   ├── main.py                 # All API routes
│   ├── database.py             # PostgreSQL connection
│   ├── models.py               # Database table definitions
│   ├── schemas.py              # Request/response validation
│   ├── auth.py                 # JWT auth + password hashing
│   ├── analyzer.py             # TF-IDF ATS scorer + Groq AI
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variables template
│
├── web-app/                    # JavaScript web frontend
│   ├── index.html              # Login, register, main UI
│   ├── style.css               # All styles
│   └── app.js                  # Auth, API calls, voice, PDF
│
├── jarvis_app.py               # Python desktop application
├── requirements.txt            # Desktop app dependencies
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| GET | /health | Health check | No |
| POST | /auth/register | Create account | No |
| POST | /auth/login | Login, get token | No |
| GET | /auth/me | Get current user | Yes |
| POST | /analyze | Run full analysis | Yes |
| GET | /history | Get all analyses | Yes |
| GET | /analysis/{id} | Get one analysis | Yes |
| DELETE | /analysis/{id} | Delete analysis | Yes |

Full interactive documentation: `https://jarvis-career-agent-production.up.railway.app/docs`

---

## How the ATS Score Works

The ATS (Applicant Tracking System) score uses real NLP techniques:

1. **TF-IDF Vectorization** — extracts the most important keywords from the job description using Term Frequency-Inverse Document Frequency weighting. High TF-IDF score = appears often in this document but rarely elsewhere = important keyword.

2. **Cosine Similarity** — converts both the resume and JD into TF-IDF vectors and measures the angle between them. Score of 1.0 = identical, 0.0 = completely different.

3. **Keyword Match Analysis** — extracts top 25 keywords from the JD and checks which ones appear in the resume, returning matched and missing lists.

4. **Final Score** — weighted average of cosine similarity (60%) and keyword match rate (40%), scaled to 0–100.

This replicates what tools like Jobscan charge $30/month for.

---

## How to Run Locally

### Backend

```bash
# Clone the repo
git clone https://github.com/Gouri257/jarvis-career-agent.git
cd jarvis-career-agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
cd backend
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your DATABASE_URL and SECRET_KEY

# Run the server
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### Web App

```bash
# In a second terminal
cd web-app
python -m http.server 5500
```

Open Chrome and go to: `http://localhost:5500`

### Desktop App

```bash
pip install customtkinter pyttsx3 SpeechRecognition reportlab
python jarvis_app.py
```

---

## Environment Variables

Create a `.env` file inside the `backend` folder:

```
DATABASE_URL=postgresql://username:password@host:5432/dbname
SECRET_KEY=your-long-random-secret-key
```

---

## Voice Commands

| Say this | JARVIS does this |
|---|---|
| "Analyze" | Starts the resume analysis |
| "What is my ATS score" | Reads your score aloud |
| "What are my skill gaps" | Reads all gaps aloud |
| "Read the first project" | Reads project 1 details |
| "Read the second project" | Reads project 2 details |
| "Download report" | Downloads the PDF |
| "Show history" | Opens analysis history |
| "Copy" | Copies results to clipboard |
| "Clear" | Resets everything |
| "Help" | Lists all commands |

---

## Deployment

| Service | Platform | Purpose |
|---|---|---|
| Frontend | Vercel | Hosts web-app/ folder |
| Backend | Railway | Runs FastAPI server |
| Database | Supabase | PostgreSQL cloud database |
| Desktop Release | GitHub Releases | .exe download |

---

## What I Learned Building This

- How to build a production REST API with FastAPI including auth, database, and validation
- How TF-IDF and cosine similarity work mathematically and how to implement them with scikit-learn
- How JWT authentication works — token creation, signing, and verification
- How to deploy a full-stack app across three different platforms (Vercel, Railway, Supabase)
- How to use the Web Speech API for both voice input and output
- How to build a Python desktop app with a non-blocking UI using threading
- How to structure a real project with separation of concerns across multiple files

---

## Author

**Gouri** — Computer Science Student  
GitHub: [@Gouri257](https://github.com/Gouri257)

---

## Version History

| Version | What changed |
|---|---|
| v1.0 | Basic Python voice bot — opens apps, tells jokes, searches web |
| v1.5 | Rebuilt as career agent — AI gap analysis + voice + PDF |
| v2.0 | Added FastAPI backend, PostgreSQL, JWT auth, ATS scoring, analysis history |
