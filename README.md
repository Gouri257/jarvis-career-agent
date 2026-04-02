# JARVIS — Career Agent 🎙

An AI-powered career assistant that helps students and job seekers 
level up their resumes by analyzing them against real job descriptions.

## What it does

JARVIS takes your resume and a job description, then tells you exactly:
- What skills you are missing for that role
- What new projects you should build to fill those gaps
- How to upgrade your existing projects to be more relevant
- A step-by-step build guide for every project suggested

## Features

- 🎙 Full two-way voice interaction — JARVIS speaks to you and listens to your commands
- 📄 Resume PDF upload or paste as text
- 🤖 AI-powered gap analysis using Groq (Llama 3.3 70B)
- 📋 Copy results to clipboard
- ⬇ Download a formatted PDF report
- 🌐 Web version deployable on Vercel
- 🖥 Desktop version built with Python and CustomTkinter

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop UI | Python, CustomTkinter |
| Voice Input | SpeechRecognition |
| Voice Output | pyttsx3 |
| Web UI | HTML, CSS, JavaScript |
| AI Model | Groq API — Llama 3.3 70B |
| PDF Export | ReportLab (Python), jsPDF (Web) |
| Deployment | Vercel |

## How to run (Desktop)

1. Clone this repo
2. Install dependencies: pip install -r requirements.txt
3. Add your Groq API key in jarvis_app.py
4. Run: python jarvis_app.py

## How to run (Web)

Open web-app/index.html in Chrome,
or visit the live demo link below.

## Live Demo

https://jarvis-career-agent.vercel.app

## Voice Commands

| Say this | JARVIS does this |
|---|---|
| "Analyze" | Starts the resume analysis |
| "What are my skill gaps" | Reads your gaps aloud |
| "Read the first project" | Reads project details |
| "Download report" | Saves the PDF |
| "Clear" | Resets everything |
| "Help" | Lists all commands |

## Built by

Gouri Sirimalla — Computer Science Student
