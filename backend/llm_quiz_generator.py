import os
import json
import random
from typing import List, Dict, Optional

from pydantic import BaseModel, ValidationError


# Prompt templates used when calling an LLM (kept here for transparency and tuning)
QUIZ_PROMPT_TEMPLATE = """
You are given the cleaned text of a Wikipedia article and its title.
Generate a quiz of 5 to 10 questions grounded in the article content. For each question provide:
- question: text
- options: list of four option texts
- answer: the correct option text
- explanation: a short factual explanation grounded in the article
- difficulty: one of [easy, medium, hard]

Also return a list of suggested related Wikipedia topics (3-6 items) based on subjects mentioned in the article.

Return valid JSON matching the following structure:
{
  "title": "...",
  "summary": "...",
  "quiz": [ {question objects} ... ],
  "related_topics": ["...", ...]
}

Use only information present in the article text. If the article does not contain enough facts for a question, skip that question.
Output JSON only, no extra commentary.
"""


class QuestionModel(BaseModel):
    question: str
    options: List[str]
    answer: str
    explanation: str
    difficulty: str


class QuizModel(BaseModel):
    title: Optional[str]
    summary: Optional[str]
    quiz: List[QuestionModel]
    related_topics: List[str]


def _fallback_generate_from_text(title: str, summary: str, clean_text: str, sections: List[str]) -> Dict:
    """A simple deterministic fallback quiz generator for testing when no LLM key is provided.

    It creates questions by selecting statements from the first few sentences and making multiple choice options by
    mixing keywords. This is NOT as good as an LLM but useful for offline testing.
    """
    sentences = [s.strip() for s in clean_text.split('.') if s.strip()]
    if not sentences:
        sentences = [summary] if summary else [title]

    num_q = min(7, max(5, len(sentences) // 3))
    quiz = []

    # Build a simple pool of candidate words for fake options
    words = set()
    for s in sentences[:20]:
        for w in s.split():
            w = w.strip(',.()"').capitalize()
            if len(w) > 3 and not w.isnumeric():
                words.add(w)
    words = list(words)[:50]

    for i in range(num_q):
        idx = i if i < len(sentences) else 0
        q_text = sentences[idx][:200].rstrip()
        if len(q_text) < 10:
            q_text = (summary or title)[:200]

        tokens = [t.strip(',.()"') for t in sentences[idx].split()]
        candidates = [t for t in tokens if t.istitle() and len(t) > 3]
        if candidates:
            correct = random.choice(candidates)
        else:
            parts = sentences[idx].split()
            correct = parts[0] if parts else title

        # build options
        options = [correct]
        while len(options) < 4:
            pick = random.choice(words) if words else f"Option{random.randint(1,99)}"
            if pick not in options:
                options.append(pick)
        random.shuffle(options)

        difficulty = random.choice(["easy"] * 3 + ["medium"] * 2 + ["hard"])
        explanation = f"Based on the article text: '{sentences[idx][:120].strip()}'."

        q = {
            "question": q_text + "?",
            "options": options,
            "answer": correct,
            "explanation": explanation,
            "difficulty": difficulty,
        }
        quiz.append(q)

    # Related topics: use section titles and some keywords
    related = []
    for s in sections[:5]:
        if s and s not in related:
            related.append(s)
    for w in words[:6]:
        if w not in related and len(related) < 6:
            related.append(w)

    return {
        "title": title,
        "summary": summary,
        "quiz": quiz,
        "related_topics": related,
    }


def _call_gemini(prompt: str) -> Optional[str]:
    """Attempt to call Google Gemini via the google.generativeai client if available.

    Returns the raw text output or None on failure.
    Requirements: pip install google-generative-ai and set environment variable GEMINI_API_KEY.
    """
    try:
        import google.generativeai as genai
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return None
        genai.configure(api_key=key)
        # model choice can be configured; use a conservative default
        model = os.getenv("GEMINI_MODEL", "models/text-bison-001")
        resp = genai.generate(model=model, prompt=prompt, max_output_tokens=800)
        # Attempt to extract text
        text = None
        if hasattr(resp, "text"):
            text = resp.text
        else:
            # some clients return a nested structure
            text = str(resp)
        return text
    except Exception:
        return None


def _call_openai(prompt: str) -> Optional[str]:
    """Call OpenAI Chat Completions directly if `openai` is installed and OPENAI_API_KEY is set.

    Returns the assistant text or None on failure.
    """
    try:
        import openai
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        openai.api_key = key
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        resp = openai.ChatCompletion.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=800)
        if resp and resp.choices:
            return resp.choices[0].message.get('content')
        return None
    except Exception:
        return None


def _parse_and_validate_json(text: str) -> Optional[Dict]:
    """Attempt to load JSON from text and validate with Pydantic schema."""
    try:
        payload = json.loads(text)
        # validate shape
        validated = QuizModel.parse_obj(payload)
        return validated.dict()
    except (json.JSONDecodeError, ValidationError):
        return None


def generate_quiz(title: str, summary: str, clean_text: str, sections: List[str]) -> Dict:
    """Top-level function to generate a quiz. Prefers Gemini, then OpenAI, falls back to deterministic generator.

    This function will attempt to call an LLM if the appropriate env var and client library are available.
    If calls fail, it returns the deterministic fallback output so the app remains functional offline.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    prompt = QUIZ_PROMPT_TEMPLATE + "\n\nARTICLE_TITLE:\n" + (title or "") + "\n\nARTICLE_TEXT:\n" + (clean_text or summary or "")

    # Try Gemini first
    if gemini_key:
        text = _call_gemini(prompt)
        if text:
            parsed = _parse_and_validate_json(text)
            if parsed:
                return parsed

    # Try OpenAI next
    if openai_key:
        text = _call_openai(prompt)
        if text:
            parsed = _parse_and_validate_json(text)
            if parsed:
                return parsed

    # Fallback deterministic generator
    return _fallback_generate_from_text(title, summary, clean_text, sections)

