"""
JARVIS Analyzer
================
Two core functions:

1. compute_ats_score()
   - Uses TF-IDF vectorization + cosine similarity (real NLP)
   - Extracts keywords from JD and resume
   - Scores match from 0-100
   - Returns grade, matched keywords, missing keywords

2. get_ai_analysis()
   - Calls Groq API (Llama 3.3 70B)
   - Returns gaps, new projects, upgrade projects as structured JSON
"""

import re
import json
import requests
from typing import Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


# ══════════════════════════════════════════════════════════════
# ATS SCORE — TF-IDF + Cosine Similarity
# ══════════════════════════════════════════════════════════════

# Words to ignore — they appear everywhere and carry no meaning
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "we", "you",
    "i", "it", "this", "that", "they", "them", "their", "our", "your",
    "as", "if", "so", "but", "not", "no", "nor", "yet", "both", "either",
    "about", "above", "across", "after", "against", "along", "among",
    "around", "before", "behind", "below", "beneath", "beside", "between",
    "beyond", "during", "except", "inside", "into", "near", "off", "out",
    "outside", "over", "past", "since", "through", "throughout", "under",
    "until", "up", "upon", "within", "without", "also", "just", "than",
    "then", "when", "where", "who", "which", "what", "how", "why",
    "while", "although", "because", "however", "therefore", "thus",
    "eg", "ie", "etc", "per", "via", "vs", "e", "g"
}


def clean_text(text: str) -> str:
    """
    Cleans text for NLP processing.
    Lowercases, removes punctuation, removes stop words.
    """
    text  = text.lower()
    text  = re.sub(r"[^a-z0-9\s\+\#]", " ", text)   # keep + and # for C++, C#
    words = text.split()
    words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return " ".join(words)


def extract_keywords(text: str, top_n: int = 30) -> list:
    """
    Uses TF-IDF to find the most important keywords in a text.

    TF-IDF explained simply:
    - TF (Term Frequency) = how often a word appears in THIS document
    - IDF (Inverse Document Frequency) = how rare the word is across documents
    - TF-IDF score = TF × IDF
    - High score = appears often in this doc but rarely elsewhere = important keyword
    """
    cleaned = clean_text(text)
    if not cleaned.strip():
        return []

    # Create TF-IDF vectorizer
    # ngram_range=(1,2) means it considers both single words AND two-word phrases
    # e.g. "machine learning" is treated as one keyword, not two separate words
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=200,
        sublinear_tf=True    # use log(tf) to reduce impact of very frequent words
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([cleaned])
        feature_names = vectorizer.get_feature_names_out()
        scores        = tfidf_matrix.toarray()[0]

        # Sort keywords by score, take top N
        top_indices = np.argsort(scores)[::-1][:top_n]
        keywords    = [feature_names[i] for i in top_indices if scores[i] > 0]
        return keywords
    except Exception:
        # Fallback: just return cleaned words if TF-IDF fails
        return cleaned.split()[:top_n]


def compute_ats_score(resume_text: str, job_description: str) -> Dict[str, Any]:
    """
    Computes an ATS compatibility score between a resume and job description.

    Steps:
    1. Clean both texts
    2. Extract keywords from JD (these are what ATS systems look for)
    3. Check which JD keywords appear in the resume
    4. Use TF-IDF + cosine similarity for the overall score
    5. Return score, grade, matched keywords, missing keywords
    """

    # If no resume provided, return zero score
    if not resume_text or len(resume_text.strip()) < 50:
        return {
            "score": 0.0,
            "grade": "F",
            "matched_keywords": [],
            "missing_keywords": extract_keywords(job_description, top_n=20),
            "explanation": "No resume provided for comparison."
        }

    cleaned_resume = clean_text(resume_text)
    cleaned_jd     = clean_text(job_description)

    # ── Step 1: Cosine Similarity Score ──
    # This measures overall text similarity using TF-IDF vectors
    try:
        vectorizer   = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        tfidf_matrix = vectorizer.fit_transform([cleaned_jd, cleaned_resume])

        # cosine_similarity returns a value between 0 and 1
        # 0 = completely different, 1 = identical
        similarity = cosine_similarity(
            tfidf_matrix[0:1],   # JD vector
            tfidf_matrix[1:2]    # Resume vector
        )[0][0]

        # Convert to 0-100 scale
        # We use a curve because raw cosine similarity tends to be low even for good matches
        # Multiplying by 150 and capping at 100 gives a more intuitive score
        raw_score = min(float(similarity) * 150, 100)

    except Exception:
        raw_score = 0.0

    # ── Step 2: Keyword Match Analysis ──
    jd_keywords     = extract_keywords(job_description, top_n=25)
    resume_keywords = set(extract_keywords(resume_text, top_n=50))
    resume_text_lower = resume_text.lower()

    matched  = []
    missing  = []

    for keyword in jd_keywords:
        # Check if keyword appears anywhere in the resume text
        if keyword in resume_text_lower or keyword in resume_keywords:
            matched.append(keyword)
        else:
            missing.append(keyword)

    # ── Step 3: Keyword Match Score ──
    keyword_score = (len(matched) / len(jd_keywords) * 100) if jd_keywords else 0

    # ── Step 4: Final Score = weighted average ──
    # 60% weight on cosine similarity (overall fit)
    # 40% weight on keyword matching (ATS keyword check)
    final_score = (raw_score * 0.6) + (keyword_score * 0.4)
    final_score = round(min(final_score, 100), 1)

    # ── Step 5: Grade ──
    if final_score >= 80:
        grade = "A"
    elif final_score >= 65:
        grade = "B"
    elif final_score >= 50:
        grade = "C"
    elif final_score >= 35:
        grade = "D"
    else:
        grade = "F"

    return {
        "score":            final_score,
        "grade":            grade,
        "matched_keywords": matched[:15],   # top 15 matched
        "missing_keywords": missing[:15],   # top 15 missing
    }


# ══════════════════════════════════════════════════════════════
# GROQ AI ANALYSIS
# ══════════════════════════════════════════════════════════════

def get_ai_analysis(
    resume_text: str,
    job_description: str,
    groq_api_key: str
) -> Dict[str, Any]:
    """
    Calls Groq API to get AI-powered gap analysis and project suggestions.
    Returns structured JSON with role, gaps, new_projects, upgrade_projects.
    """

    resume_section = ""
    if resume_text and len(resume_text.strip()) > 50:
        resume_section = (
            f"\nCandidate Resume:\n---\n{resume_text}\n---\n"
            "Analyze this resume carefully and give personalised suggestions."
        )
    else:
        resume_section = (
            "\nNo resume provided. Generate suggestions based on the job description alone. "
            "Set upgrade_projects to an empty array."
        )

    system_prompt = """You are JARVIS, an expert career coach AI.
Analyze the candidate profile against the job description.
Return ONLY a valid JSON object. No markdown. No explanation. Just raw JSON.

Structure:
{
  "role": "exact job title from the JD",
  "gaps": [
    {"skill": "skill name", "reason": "why this matters for this specific role"}
  ],
  "new_projects": [
    {
      "title": "specific project name",
      "why": "one sentence why this impresses for this exact role",
      "tech": ["tech1", "tech2", "tech3"],
      "steps": ["step 1", "step 2", "step 3", "step 4"]
    }
  ],
  "upgrade_projects": [
    {
      "title": "existing project + what to add",
      "why": "why this upgrade matters",
      "tech": ["tech1"],
      "steps": ["step 1", "step 2", "step 3"]
    }
  ]
}

Rules:
- 3 to 4 skill gaps
- 2 to 3 new projects
- 1 to 2 upgrade projects (or empty array if no resume)
- Be specific to this JD
- Steps must be concrete and actionable"""

    user_message = (
        f"Job Description:\n{job_description}\n{resume_section}\n"
        "Analyze and return the JSON now."
    )

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {groq_api_key}",
        },
        json={
            "model":       "llama-3.3-70b-versatile",
            "messages":    [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            "max_tokens":  1500,
            "temperature": 0.7,
        },
        timeout=30
    )

    data = response.json()

    if "error" in data:
        raise Exception(f"Groq API error: {data['error']['message']}")

    raw_text = data["choices"][0]["message"]["content"]
    clean    = re.sub(r"```json|```", "", raw_text).strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        raise Exception("Could not parse AI response as JSON. Please try again.")
