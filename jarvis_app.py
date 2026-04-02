"""
JARVIS Career Agent — Desktop App
===================================
Requirements (install once):
    pip install customtkinter requests pyttsx3 SpeechRecognition reportlab PyMuPDF

Run:
    python jarvis_app.py
"""

# ── Standard library ──────────────────────────────────────────
import threading
import json
import os
import re
import datetime

# ── GUI ───────────────────────────────────────────────────────
import tkinter as tk
from tkinter import filedialog, scrolledtext
import customtkinter as ctk

# ── Voice ─────────────────────────────────────────────────────
import pyttsx3
import speech_recognition as sr

# ── AI + PDF ──────────────────────────────────────────────────
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "paste-your-key-here")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ══════════════════════════════════════════════════════════════
# VOICE ENGINE  (runs in its own thread so it never freezes UI)
# ══════════════════════════════════════════════════════════════

class VoiceEngine:
    """Handles TTS (speak) and STT (listen) in background threads."""

    def __init__(self):
        self.is_muted  = False
        self._init_tts()

    def _init_tts(self):
        """We no longer keep a persistent engine — we create one per speak call."""
        self.preferred_voice_id = None

        # Do a one-time scan to find the best voice
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower() or "english" in v.name.lower():
                    self.preferred_voice_id = v.id
                    break
            temp_engine.stop()
            del temp_engine
        except Exception as e:
            print(f"Voice scan error: {e}")

    def speak(self, text, on_done=None):
        """Speak text in a background thread using a FRESH engine each time."""
        if self.is_muted:
            if on_done:
                on_done()
            return

        def _speak():
            try:
                # Create a brand new engine every single time
                engine = pyttsx3.init()

                if self.preferred_voice_id:
                    engine.setProperty("voice", self.preferred_voice_id)

                engine.setProperty("rate", 175)
                engine.setProperty("volume", 1.0)

                engine.say(text)
                engine.runAndWait()

                # Clean up properly
                engine.stop()
                del engine

            except Exception as e:
                print(f"TTS speak error: {e}")
            finally:
                if on_done:
                    on_done()

        t = threading.Thread(target=_speak, daemon=True)
        t.start()

    def listen(self, on_result, on_error):
        """Listen via microphone in a background thread."""
        def _listen():
            r      = sr.Recognizer()
            r.pause_threshold = 1.0        # seconds of silence before stopping
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=8, phrase_time_limit=15)
                text = r.recognize_google(audio)
                on_result(text)
            except sr.WaitTimeoutError:
                on_error("No speech detected. Please try again.")
            except sr.UnknownValueError:
                on_error("Could not understand. Please speak clearly.")
            except sr.RequestError as e:
                on_error(f"Speech service error: {e}")
            except Exception as e:
                on_error(f"Microphone error: {e}")

        t = threading.Thread(target=_listen, daemon=True)
        t.start()


# ══════════════════════════════════════════════════════════════
# GROQ AI CALLER
# ══════════════════════════════════════════════════════════════

def call_groq(system_prompt, user_message):
    """
    Calls the Groq API and returns the response text.
    Raises an Exception with a readable message on failure.
    """
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens":  1500,
        "temperature": 0.7,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    data = resp.json()

    if "error" in data:
        raise Exception(data["error"]["message"])

    return data["choices"][0]["message"]["content"]


# ══════════════════════════════════════════════════════════════
# PDF REPORT GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_pdf(result: dict, save_path: str):
    """Creates a formatted PDF report from the analysis result dict."""

    doc    = SimpleDocTemplate(save_path, pagesize=A4,
                               leftMargin=20*mm, rightMargin=20*mm,
                               topMargin=20*mm,  bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story  = []

    # ── Custom styles ──
    title_style = ParagraphStyle(
        "JarvisTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "JarvisSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#555555"),
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=10,
        textColor=colors.HexColor("#888888"),
        spaceBefore=16,
        spaceAfter=6,
        borderPad=4,
    )
    skill_name_style = ParagraphStyle(
        "SkillName",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#cc4400"),
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#444444"),
        leading=15,
        spaceAfter=4,
    )
    project_title_style = ParagraphStyle(
        "ProjTitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#1155aa"),
        fontName="Helvetica-Bold",
        spaceAfter=3,
    )
    step_style = ParagraphStyle(
        "Step",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#444444"),
        leading=14,
        leftIndent=12,
        spaceAfter=2,
    )

    # ── Header block ──
    story.append(Paragraph("JARVIS — Career Agent", title_style))
    story.append(Paragraph("Resume Analysis Report", subtitle_style))

    date_str = datetime.datetime.now().strftime("%d %B %Y")
    story.append(Paragraph(f"Generated: {date_str}", subtitle_style))

    # Horizontal rule
    story.append(Table(
        [[""]],
        colWidths=[170*mm],
        style=TableStyle([
            ("LINEBELOW", (0,0), (-1,-1), 1, colors.HexColor("#dddddd")),
        ])
    ))
    story.append(Spacer(1, 8*mm))

    # ── Role ──
    story.append(Paragraph(f"Target Role: {result.get('role', 'Unknown')}", title_style))
    story.append(Spacer(1, 4*mm))

    # ── Skill Gaps ──
    story.append(Paragraph("SKILL GAPS", section_style))
    for gap in result.get("gaps", []):
        story.append(Paragraph(gap["skill"], skill_name_style))
        story.append(Paragraph(gap["reason"], body_style))
        story.append(Spacer(1, 3*mm))

    # ── New Projects ──
    story.append(Paragraph("PROJECTS TO BUILD", section_style))
    for i, p in enumerate(result.get("new_projects", []), 1):
        story.append(Paragraph(f"{i}. {p['title']}", project_title_style))
        story.append(Paragraph(p["why"], body_style))
        story.append(Paragraph(
            f"<font color='#888888'>Tech: {', '.join(p.get('tech', []))}</font>",
            body_style
        ))
        for j, step in enumerate(p.get("steps", []), 1):
            story.append(Paragraph(f"{j}. {step}", step_style))
        story.append(Spacer(1, 4*mm))

    # ── Upgrade Projects ──
    upgrades = result.get("upgrade_projects", [])
    if upgrades:
        story.append(Paragraph("PROJECTS TO UPGRADE", section_style))
        for i, p in enumerate(upgrades, 1):
            story.append(Paragraph(f"{i}. {p['title']}", project_title_style))
            story.append(Paragraph(p["why"], body_style))
            story.append(Paragraph(
                f"<font color='#888888'>Tech: {', '.join(p.get('tech', []))}</font>",
                body_style
            ))
            for j, step in enumerate(p.get("steps", []), 1):
                story.append(Paragraph(f"{j}. {step}", step_style))
            story.append(Spacer(1, 4*mm))

    # ── Footer ──
    story.append(Spacer(1, 8*mm))
    story.append(Table(
        [[""]],
        colWidths=[170*mm],
        style=TableStyle([
            ("LINEABOVE", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ])
    ))
    story.append(Paragraph(
        "Generated by JARVIS Career Agent",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontSize=8, textColor=colors.HexColor("#aaaaaa"),
                       alignment=1)
    ))

    doc.build(story)


# ══════════════════════════════════════════════════════════════
# MAIN APPLICATION WINDOW
# ══════════════════════════════════════════════════════════════

class JarvisApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ── Window setup ──
        self.title("JARVIS — Career Agent")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # ── State ──
        self.voice_engine    = VoiceEngine()
        self.last_result     = None    # stores the last JSON analysis
        self.resume_filepath = None    # path to uploaded PDF
        self.is_listening    = False

        # ── Build UI ──
        self._build_header()
        self._build_main()
        self._build_status_bar()

        # ── Greet user ──
        self.after(800, lambda: self._jarvis_speak(
            "Hello. I am JARVIS, your career assistant. "
            "Paste your resume text and the job description, "
            "then click Analyze, or press the microphone button."
        ))

    # ──────────────────────────────────────────────────────────
    # UI BUILDERS
    # ──────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, height=56, corner_radius=0,
                              fg_color=("#111111", "#111111"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⬡  JARVIS — Career Agent",
            font=ctk.CTkFont(family="Courier", size=16, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=20)

        self.status_pill = ctk.CTkLabel(
            header, text="standby",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            fg_color=("#222222", "#222222"),
            corner_radius=12,
            width=80, height=24
        )
        self.status_pill.pack(side="right", padx=20)

        # Mute button in header
        self.mute_btn = ctk.CTkButton(
            header, text="🔊", width=36, height=28,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=("#333333", "#333333"),
            command=self._toggle_mute
        )
        self.mute_btn.pack(side="right", padx=4)

    def _build_main(self):
        """Two-column layout: left = inputs, right = voice + results."""
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=12)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self._build_left_panel(main)
        self._build_right_panel(main)

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.rowconfigure(4, weight=1)   # JD textarea expands
        left.columnconfigure(0, weight=1)

        # ── PDF Upload ──
        self._label(left, "STEP 1 — Upload Resume PDF (optional)").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        upload_row = ctk.CTkFrame(left, fg_color="transparent")
        upload_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0,8))
        upload_row.columnconfigure(0, weight=1)

        self.upload_btn = ctk.CTkButton(
            upload_row, text="📄  Choose PDF file",
            command=self._choose_pdf,
            height=36, fg_color=("#2a2a2a","#2a2a2a"),
            hover_color=("#3a3a3a","#3a3a3a"),
            border_width=1, border_color=("#444","#444")
        )
        self.upload_btn.grid(row=0, column=0, sticky="ew")

        self.pdf_label = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=11),
            text_color="#22cc77"
        )
        self.pdf_label.grid(row=2, column=0, sticky="w", padx=16, pady=(0,4))

        # ── Resume text ──
        self._label(left, "STEP 2 — Paste Your Resume Text (recommended)").grid(
            row=3, column=0, sticky="w", padx=16, pady=(8,4))

        self.resume_text = ctk.CTkTextbox(
            left, height=140,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.resume_text.grid(row=4, column=0, sticky="nsew", padx=16)
        self.resume_text.insert("0.0",
            "Paste your full resume here — skills, experience, projects, education...")

        # ── Job Description ──
        self._label(left, "STEP 3 — Paste the Job Description").grid(
            row=5, column=0, sticky="w", padx=16, pady=(12,4))

        self.jd_text = ctk.CTkTextbox(
            left, height=140,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.jd_text.grid(row=6, column=0, sticky="ew", padx=16)
        self.jd_text.insert("0.0",
            "Paste the full job description or internship posting here...")

        # ── Action buttons ──
        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.grid(row=7, column=0, sticky="ew", padx=16, pady=12)
        btn_row.columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="Clear", width=80,
            fg_color=("#2a2a2a","#2a2a2a"),
            hover_color=("#3a3a3a","#3a3a3a"),
            command=self._clear_all
        ).grid(row=0, column=0, padx=(0,8))

        ctk.CTkButton(
            btn_row, text="Analyze My Resume  →",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_analysis
        ).grid(row=0, column=1, sticky="ew")

    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(parent, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        # ── JARVIS voice panel ──
        voice_panel = ctk.CTkFrame(
            right, corner_radius=10,
            fg_color=("#0d0d0d","#0d0d0d")
        )
        voice_panel.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        voice_panel.columnconfigure(0, weight=1)

        # Orb (just a label with emoji that changes)
        self.orb_label = ctk.CTkLabel(
            voice_panel, text="◉",
            font=ctk.CTkFont(family="Courier", size=36),
            text_color="#1188cc"
        )
        self.orb_label.grid(row=0, column=0, pady=(14,4))

        self.jarvis_state_label = ctk.CTkLabel(
            voice_panel,
            text="JARVIS READY",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color="#445566"
        )
        self.jarvis_state_label.grid(row=1, column=0, pady=(0,8))

        # What JARVIS said
        self.speech_bubble = ctk.CTkTextbox(
            voice_panel, height=52,
            font=ctk.CTkFont(size=11, slant="italic"),
            fg_color=("#161616","#161616"),
            text_color="#88aacc",
            wrap="word",
            state="disabled"
        )
        self.speech_bubble.grid(row=2, column=0, sticky="ew", padx=12, pady=(0,10))

        # Mic button + transcript
        mic_row = ctk.CTkFrame(voice_panel, fg_color="transparent")
        mic_row.grid(row=3, column=0, pady=(0,10), padx=12)

        self.mic_btn = ctk.CTkButton(
            mic_row, text="🎙  Hold to Speak",
            width=160, height=34,
            font=ctk.CTkFont(size=12),
            fg_color=("#1a1a1a","#1a1a1a"),
            hover_color=("#2a2a2a","#2a2a2a"),
            border_width=1, border_color=("#333","#333"),
            command=self._toggle_listening
        )
        self.mic_btn.pack(side="left", padx=(0,8))

        # Voice transcript (what user said)
        self.transcript_label = ctk.CTkLabel(
            voice_panel, text="",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#556677",
            wraplength=280
        )
        self.transcript_label.grid(row=4, column=0, pady=(0,6))

        # Hint chips
        hints_frame = ctk.CTkFrame(voice_panel, fg_color="transparent")
        hints_frame.grid(row=5, column=0, pady=(0,12), padx=12)

        hints = ['"Analyze"', '"Read first project"',
                 '"Skill gaps"', '"Download report"', '"Clear"']
        for i, hint in enumerate(hints):
            ctk.CTkLabel(
                hints_frame, text=hint,
                font=ctk.CTkFont(family="Courier", size=9),
                text_color="#445566",
                fg_color=("#141414","#141414"),
                corner_radius=8,
                padx=6, pady=2
            ).grid(row=i//3, column=i%3, padx=3, pady=2, sticky="w")

        # ── Result action buttons ──
        self.action_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.action_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,4))

        self.copy_btn = ctk.CTkButton(
            self.action_frame, text="📋  Copy Results",
            width=130, height=30,
            font=ctk.CTkFont(size=11),
            fg_color=("#2a2a2a","#2a2a2a"),
            hover_color=("#3a3a3a","#3a3a3a"),
            state="disabled",
            command=self._copy_results
        )
        self.copy_btn.pack(side="left", padx=(0,8))

        self.pdf_btn = ctk.CTkButton(
            self.action_frame, text="⬇  Download PDF",
            width=140, height=30,
            font=ctk.CTkFont(size=11),
            fg_color=("#2a2a2a","#2a2a2a"),
            hover_color=("#3a3a3a","#3a3a3a"),
            state="disabled",
            command=self._download_pdf
        )
        self.pdf_btn.pack(side="left")

        # ── Results display ──
        self.results_box = ctk.CTkTextbox(
            right, font=ctk.CTkFont(size=12),
            wrap="word", state="disabled"
        )
        self.results_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0,12))

        self._set_results_text(
            "Upload your resume and paste a job description,\n"
            "then click Analyze My Resume or use your voice."
        )

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, height=28, corner_radius=0,
                           fg_color=("#1a1a1a","#1a1a1a"))
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_bar_label = ctk.CTkLabel(
            bar, text="Ready",
            font=ctk.CTkFont(size=10),
            text_color="#556677"
        )
        self.status_bar_label.pack(side="left", padx=12)

    # ──────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────

    def _label(self, parent, text):
        return ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=10),
            text_color="#777777"
        )

    def _set_status(self, text, color="#888888"):
        self.status_pill.configure(text=text, text_color=color)
        self.status_bar_label.configure(text=text)

    def _set_jarvis_state(self, text, orb_color="#1188cc"):
        self.jarvis_state_label.configure(text=text.upper())
        self.orb_label.configure(text_color=orb_color)

    def _set_results_text(self, text):
        self.results_box.configure(state="normal")
        self.results_box.delete("0.0", "end")
        self.results_box.insert("0.0", text)
        self.results_box.configure(state="disabled")

    def _show_speech_bubble(self, text):
        self.speech_bubble.configure(state="normal")
        self.speech_bubble.delete("0.0", "end")
        self.speech_bubble.insert("0.0", text)
        self.speech_bubble.configure(state="disabled")

    def _get_resume_text(self):
        t = self.resume_text.get("0.0", "end").strip()
        placeholder = "Paste your full resume here"
        return "" if t.startswith(placeholder) else t

    def _get_jd_text(self):
        t = self.jd_text.get("0.0", "end").strip()
        placeholder = "Paste the full job description"
        return "" if t.startswith(placeholder) else t

    # ──────────────────────────────────────────────────────────
    # JARVIS SPEAK
    # ──────────────────────────────────────────────────────────

    def _jarvis_speak(self, text, on_done=None):
        """Show text in bubble + speak it aloud."""
        self._show_speech_bubble(text)
        self._set_jarvis_state("Speaking...", "#22cc77")

        def _after_speak():
            self._set_jarvis_state("JARVIS Ready", "#1188cc")
            if on_done:
                self.after(0, on_done)

        self.voice_engine.speak(text, on_done=_after_speak)

    def _toggle_mute(self):
        self.voice_engine.is_muted = not self.voice_engine.is_muted
        if self.voice_engine.is_muted:
            self.mute_btn.configure(text="🔇")
            self._set_jarvis_state("Muted", "#555555")
        else:
            self.mute_btn.configure(text="🔊")
            self._set_jarvis_state("JARVIS Ready", "#1188cc")

    # ──────────────────────────────────────────────────────────
    # VOICE INPUT
    # ──────────────────────────────────────────────────────────

    def _toggle_listening(self):
        if self.is_listening:
            return   # already listening — ignore double clicks
        self.is_listening = True
        self.mic_btn.configure(
            text="⏹  Listening...",
            fg_color=("#1a0505","#1a0505"),
            border_color=("#cc3322","#cc3322")
        )
        self._set_jarvis_state("Listening...", "#cc2211")
        self.transcript_label.configure(text="")
        self._set_status("Listening...")

        self.voice_engine.listen(
            on_result=self._on_voice_result,
            on_error=self._on_voice_error
        )

    def _on_voice_result(self, text):
        """Called from background thread when speech is recognised."""
        # Always update UI from main thread
        self.after(0, lambda: self._handle_voice_result(text))

    def _on_voice_error(self, msg):
        self.after(0, lambda: self._handle_voice_error(msg))

    def _handle_voice_result(self, text):
        self.transcript_label.configure(text=f'You said: "{text}"')
        self._reset_mic_btn()
        self._handle_voice_command(text.lower().strip())

    def _handle_voice_error(self, msg):
        self.transcript_label.configure(text=msg)
        self._reset_mic_btn()
        self._set_jarvis_state("JARVIS Ready", "#1188cc")
        self._set_status("Ready")

    def _reset_mic_btn(self):
        self.is_listening = False
        self.mic_btn.configure(
            text="🎙  Hold to Speak",
            fg_color=("#1a1a1a","#1a1a1a"),
            border_color=("#333","#333")
        )

    # ──────────────────────────────────────────────────────────
    # VOICE COMMAND HANDLER
    # ──────────────────────────────────────────────────────────

    def _handle_voice_command(self, cmd):
        print(f"[Voice] {cmd}")

        if any(w in cmd for w in ["analyze", "start", "go"]):
            self._jarvis_speak("Starting analysis now. Please wait.",
                               on_done=self._start_analysis)

        elif any(w in cmd for w in ["gap", "missing", "skill"]):
            if self.last_result:
                gaps = ", ".join(g["skill"] for g in self.last_result.get("gaps", []))
                self._jarvis_speak(f"Your skill gaps are: {gaps}.")
            else:
                self._jarvis_speak("No analysis yet. Please paste a job description and say analyze.")

        elif any(w in cmd for w in ["project", "first", "second", "third"]):
            projects = (self.last_result or {}).get("new_projects", [])
            idx = 1 if "second" in cmd else 2 if "third" in cmd else 0
            if projects and idx < len(projects):
                p     = projects[idx]
                steps = ". ".join(p["steps"][:3])
                self._jarvis_speak(
                    f"Project {idx+1}: {p['title']}. {p['why']}. "
                    f"Tech stack: {', '.join(p['tech'])}. "
                    f"First steps: {steps}."
                )
            else:
                self._jarvis_speak("No projects found yet. Please run an analysis first.")

        elif any(w in cmd for w in ["download", "save", "report", "pdf"]):
            if self.last_result:
                self._jarvis_speak("Downloading your report now.")
                self.after(500, self._download_pdf)
            else:
                self._jarvis_speak("No report yet. Please run an analysis first.")

        elif "copy" in cmd:
            if self.last_result:
                self._jarvis_speak("Copying results to clipboard.")
                self.after(500, self._copy_results)
            else:
                self._jarvis_speak("Nothing to copy yet.")

        elif any(w in cmd for w in ["clear", "reset", "start over"]):
            self._jarvis_speak("Clearing everything.",
                               on_done=self._clear_all)

        elif any(w in cmd for w in ["hello", "hi", "hey"]):
            self._jarvis_speak(
                "Hello! I am JARVIS. Paste your resume and job description, "
                "then say analyze to get started."
            )

        elif any(w in cmd for w in ["help", "what can you do", "commands"]):
            self._jarvis_speak(
                "Say: analyze to start. "
                "Skill gaps to hear your gaps. "
                "Read first project to hear details. "
                "Download report to save a PDF. "
                "Clear to reset."
            )

        else:
            # Treat as job description input
            current = self._get_jd_text()
            self.jd_text.configure(state="normal")
            if not current:
                self.jd_text.delete("0.0", "end")
                self.jd_text.insert("0.0", cmd)
                self._jarvis_speak("Added to the job description. Say analyze when ready.")
            else:
                self.jd_text.insert("end", " " + cmd)
                self._jarvis_speak("Appended to job description. Say analyze when ready.")

    # ──────────────────────────────────────────────────────────
    # PDF UPLOAD
    # ──────────────────────────────────────────────────────────

    def _choose_pdf(self):
        path = filedialog.askopenfilename(
            title="Select your resume PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if path:
            self.resume_filepath = path
            name = os.path.basename(path)
            self.pdf_label.configure(text=f"✓  {name}")
            self._jarvis_speak(f"Resume {name} loaded. Now paste the job description and say analyze.")

    # ──────────────────────────────────────────────────────────
    # MAIN ANALYSIS
    # ──────────────────────────────────────────────────────────

    def _start_analysis(self):
        jd = self._get_jd_text()
        if not jd:
            self._jarvis_speak("Please paste a job description first.")
            return

        # Disable button, update status
        self._set_status("Analyzing...", "#22cc77")
        self._set_jarvis_state("Analyzing...", "#22cc77")
        self._set_results_text("⏳  Analyzing your resume against the job description...\n\nThis takes about 5–10 seconds.")

        # Run in background thread so UI doesn't freeze
        threading.Thread(target=self._run_analysis_thread, daemon=True).start()

    def _run_analysis_thread(self):
        """Runs in a background thread — never touches UI directly."""
        try:
            resume_text = self._get_resume_text()
            jd_text     = self._get_jd_text()

            # Build resume section
            if resume_text:
                resume_section = (
                    "\nHere is the candidate's resume:\n---\n"
                    + resume_text +
                    "\n---\nAnalyze carefully and give personalised gaps and project ideas."
                )
            else:
                resume_section = (
                    "\nNo resume provided. "
                    "Generate suggestions from the job description alone. "
                    "Set upgrade_projects to an empty array."
                )

            system_prompt = (
                "You are JARVIS, an expert career coach AI.\n"
                "Analyze the candidate profile against the job description.\n"
                "Return ONLY a valid JSON object. No markdown. No explanation. Just raw JSON.\n\n"
                "Structure:\n"
                "{\n"
                '  "role": "exact job title from the JD",\n'
                '  "gaps": [\n'
                '    {"skill": "skill name", "reason": "why this matters for this role"}\n'
                "  ],\n"
                '  "new_projects": [\n'
                "    {\n"
                '      "title": "specific project name",\n'
                '      "why": "one sentence why this impresses for this exact role",\n'
                '      "tech": ["tech1", "tech2", "tech3"],\n'
                '      "steps": ["step 1", "step 2", "step 3", "step 4"]\n'
                "    }\n"
                "  ],\n"
                '  "upgrade_projects": [\n'
                "    {\n"
                '      "title": "existing project + what to add",\n'
                '      "why": "why this upgrade matters",\n'
                '      "tech": ["tech1"],\n'
                '      "steps": ["step 1", "step 2", "step 3"]\n'
                "    }\n"
                "  ]\n"
                "}\n\n"
                "Rules: 3–4 gaps, 2–3 new projects, 1–2 upgrade projects (or []).\n"
                "Be specific to this JD. Steps must be concrete and actionable.\n\n"
                f"Job Description:\n{jd_text}\n{resume_section}"
            )

            raw = call_groq(system_prompt, "Analyze and return the JSON now.")
            clean = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(clean)

            # Schedule UI update on main thread
            self.after(0, lambda: self._on_analysis_done(result))

        except json.JSONDecodeError:
            self.after(0, lambda: self._on_analysis_error(
                "Could not parse AI response as JSON. Please try again."
            ))
        except Exception as e:
            self.after(0, lambda: self._on_analysis_error(str(e)))

    def _on_analysis_done(self, result):
        self.last_result = result

        # Build readable text for the results box
        lines = []
        lines.append(f"TARGET ROLE: {result.get('role', '?').upper()}")
        lines.append("=" * 50)

        lines.append("\n── SKILL GAPS ──")
        for i, g in enumerate(result.get("gaps", []), 1):
            lines.append(f"\n{i}. {g['skill']}")
            lines.append(f"   {g['reason']}")

        lines.append("\n── PROJECTS TO BUILD ──")
        for i, p in enumerate(result.get("new_projects", []), 1):
            lines.append(f"\n{i}. {p['title']}  [NEW]")
            lines.append(f"   {p['why']}")
            lines.append(f"   Tech: {', '.join(p.get('tech', []))}")
            for j, s in enumerate(p.get("steps", []), 1):
                lines.append(f"   {j}. {s}")

        upgrades = result.get("upgrade_projects", [])
        if upgrades:
            lines.append("\n── PROJECTS TO UPGRADE ──")
            for i, p in enumerate(upgrades, 1):
                lines.append(f"\n{i}. {p['title']}  [UPGRADE]")
                lines.append(f"   {p['why']}")
                lines.append(f"   Tech: {', '.join(p.get('tech', []))}")
                for j, s in enumerate(p.get("steps", []), 1):
                    lines.append(f"   {j}. {s}")

        self._set_results_text("\n".join(lines))
        self._set_status("Complete", "#22cc77")
        self.copy_btn.configure(state="normal")
        self.pdf_btn.configure(state="normal")

        # JARVIS speaks the summary
        n_gaps     = len(result.get("gaps", []))
        n_projects = len(result.get("new_projects", []))
        first_proj = result.get("new_projects", [{}])[0].get("title", "some projects")
        role       = result.get("role", "this role")

        self._jarvis_speak(
            f"Analysis complete for {role}. "
            f"I found {n_gaps} skill gaps and {n_projects} projects for you to build. "
            f"The first project is {first_proj}. "
            "Say read the first project for details, or click Download PDF to save your report."
        )

    def _on_analysis_error(self, msg):
        self._set_results_text(f"⚠️  Error:\n\n{msg}")
        self._set_status("Error", "#cc4444")
        self._set_jarvis_state("JARVIS Ready", "#1188cc")
        self._jarvis_speak(f"There was an error: {msg}")

    # ──────────────────────────────────────────────────────────
    # COPY RESULTS
    # ──────────────────────────────────────────────────────────

    def _copy_results(self):
        if not self.last_result:
            return
        r    = self.last_result
        text = f"JARVIS CAREER ANALYSIS\n{'='*40}\nRole: {r['role']}\n\n"
        text += "SKILL GAPS\n" + "-"*30 + "\n"
        for i, g in enumerate(r.get("gaps", []), 1):
            text += f"{i}. {g['skill']}\n   {g['reason']}\n\n"
        text += "PROJECTS TO BUILD\n" + "-"*30 + "\n"
        for i, p in enumerate(r.get("new_projects", []), 1):
            text += f"{i}. {p['title']}\n   Why: {p['why']}\n"
            text += f"   Tech: {', '.join(p.get('tech',[]))}\n   Steps:\n"
            for j, s in enumerate(p.get("steps", []), 1):
                text += f"     {j}. {s}\n"
            text += "\n"
        if r.get("upgrade_projects"):
            text += "PROJECTS TO UPGRADE\n" + "-"*30 + "\n"
            for i, p in enumerate(r["upgrade_projects"], 1):
                text += f"{i}. {p['title']}\n   Why: {p['why']}\n"
                text += f"   Tech: {', '.join(p.get('tech',[]))}\n   Steps:\n"
                for j, s in enumerate(p.get("steps", []), 1):
                    text += f"     {j}. {s}\n"
                text += "\n"

        self.clipboard_clear()
        self.clipboard_append(text)
        self.copy_btn.configure(text="✓  Copied!")
        self.after(2500, lambda: self.copy_btn.configure(text="📋  Copy Results"))

    # ──────────────────────────────────────────────────────────
    # DOWNLOAD PDF
    # ──────────────────────────────────────────────────────────

    def _download_pdf(self):
        if not self.last_result:
            return
        role     = self.last_result.get("role", "Report").replace(" ", "_")
        default  = f"JARVIS_Analysis_{role}.pdf"
        save_path = filedialog.asksaveasfilename(
            title="Save PDF Report",
            defaultextension=".pdf",
            initialfile=default,
            filetypes=[("PDF files", "*.pdf")]
        )
        if not save_path:
            return
        try:
            generate_pdf(self.last_result, save_path)
            self._jarvis_speak(f"PDF report saved successfully.")
            self.pdf_btn.configure(text="✓  Saved!")
            self.after(2500, lambda: self.pdf_btn.configure(text="⬇  Download PDF"))
        except Exception as e:
            self._jarvis_speak(f"Could not save PDF: {e}")

    # ──────────────────────────────────────────────────────────
    # CLEAR
    # ──────────────────────────────────────────────────────────

    def _clear_all(self):
        self.last_result     = None
        self.resume_filepath = None
        self.pdf_label.configure(text="")

        self.resume_text.delete("0.0", "end")
        self.resume_text.insert("0.0",
            "Paste your full resume here — skills, experience, projects, education...")

        self.jd_text.delete("0.0", "end")
        self.jd_text.insert("0.0",
            "Paste the full job description or internship posting here...")

        self._set_results_text(
            "Upload your resume and paste a job description,\n"
            "then click Analyze My Resume or use your voice."
        )
        self.copy_btn.configure(state="disabled")
        self.pdf_btn.configure(state="disabled")
        self.transcript_label.configure(text="")
        self._show_speech_bubble("")
        self._set_status("Ready")
        self._set_jarvis_state("JARVIS Ready", "#1188cc")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()