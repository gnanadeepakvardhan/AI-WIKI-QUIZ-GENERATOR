# AI Wiki Quiz Generator (DeepKlarity Technologies)

This project is a minimal end-to-end implementation of the assignment: it includes a Python FastAPI backend that scrapes Wikipedia pages, generates quizzes (via a fallback generator; LangChain hooks included), stores results in a database, and a static frontend (no Node) that calls the API.

Quick start (Windows, cmd.exe):

1. Backend virtual env and install...

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. (Optional) Create `.env` based on `.env.example` and set GEMINI_API_KEY or OPENAI_API_KEY if you want LLM usage.

3. Run server

```
set DATABASE_URL=sqlite:///./quiz_history.db
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

4. Open the frontend in your browser:

http://localhost:8000/

Files of interest:
- `backend/scraper.py` — BeautifulSoup scraper for Wikipedia
- `backend/llm_quiz_generator.py` — prompt templates and fallback quiz generator (also where you'd wire LangChain/Gemini)
- `backend/main.py` — FastAPI app with `/generate_quiz`, `/history`, `/quiz/{id}` endpoints and static file serving
- `frontend/index.html`, `frontend/app.js`, `frontend/styles.css` — minimal UI with tabs and modal

Notes and assumptions:
- For demo ease the default DB is SQLite. To use Postgres or MySQL, set `DATABASE_URL` in `.env` (e.g., `postgresql://user:pass@localhost/dbname`).
- LangChain prompt template is included in `llm_quiz_generator.py`. If you supply `GEMINI_API_KEY` or `OPENAI_API_KEY` and expand the LangChain code, the service will call the LLM; otherwise it uses a deterministic fallback generator so the app functions offline.
- The scraper uses HTML scraping (BeautifulSoup) and does not use the Wikipedia API.

What I implemented beyond the assignment minimum:
- Static frontend served by FastAPI to avoid requiring Node.js.
- Storage of raw HTML in the DB (field `scraped_content`).

Next steps / improvements you can enable:
- Wire LangChain + Gemini/OpenAI for higher-quality quiz generation (see prompt in `llm_quiz_generator.py`).
- Add unit tests and CI, add optional "Take Quiz" mode to the frontend.

