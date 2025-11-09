import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import SessionLocal, init_db
from . import models
from .scraper import scrape_wikipedia, is_wikipedia_url
from .llm_quiz_generator import generate_quiz

import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

app = FastAPI(title="AI Wiki Quiz Generator")

origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:8000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class URLInput(BaseModel):
    url: str


@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/generate_quiz")
async def generate_quiz_endpoint(payload: URLInput):
    url = payload.url.strip()
    if not is_wikipedia_url(url):
        raise HTTPException(status_code=400, detail="Provided URL is not a Wikipedia URL")

    try:
        scraped = scrape_wikipedia(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error scraping URL: {e}")

    # Generate quiz using LLM or fallback
    result = generate_quiz(
        scraped.get("title", ""),
        scraped.get("summary", ""),
        scraped.get("clean_text", ""),
        scraped.get("sections", []),
    )

    print("✅ QUIZ GENERATED:", json.dumps(result, indent=2)[:500])  # debug line

    # Build full payload to store
    full = {
        "url": url,
        "title": result.get("title") or scraped.get("title"),
        "summary": result.get("summary") or scraped.get("summary"),
        "key_entities": {},
        "sections": scraped.get("sections", []),
        "quiz": result.get("quiz"),
        "related_topics": result.get("related_topics", []),
        "scraped_raw_html": scraped.get("raw_html"),
    }

    # Save to DB
    db: Session = next(get_db())
    q = models.Quiz(
        url=url,
        title=full["title"],
        scraped_content=full.get("scraped_raw_html"),
        full_quiz_data=json.dumps(full, ensure_ascii=False),
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    out = {"id": q.id, **full}
    return JSONResponse(content=out)


    # Generate quiz using LLM or fallback
    result = generate_quiz(
    scraped.get("title", ""),
    scraped.get("summary", ""),
    scraped.get("clean_text", ""),
    scraped.get("sections", []),
)

    print("✅ QUIZ GENERATED:", json.dumps(result, indent=2)[:500])  # debug print


    # Build full payload to store
    full = {
        "url": url,
        "title": result.get("title") or scraped.get("title"),
        "summary": result.get("summary") or scraped.get("summary"),
        "key_entities": {},
        "sections": scraped.get("sections", []),
        "quiz": result.get("quiz"),
        "related_topics": result.get("related_topics", []),
        "scraped_raw_html": scraped.get("raw_html"),
    }

    # Save to DB
    db: Session = next(get_db())
    q = models.Quiz(
        url=url,
        title=full["title"],
        scraped_content=full.get("scraped_raw_html"),
        full_quiz_data=json.dumps(full, ensure_ascii=False),
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    out = {"id": q.id, **full}
    return JSONResponse(content=out)


@app.get("/history")
async def history():
    db: Session = next(get_db())
    rows = db.query(models.Quiz).order_by(models.Quiz.date_generated.desc()).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "url": r.url,
            "title": r.title,
            "date_generated": r.date_generated.isoformat(),
        })
    return JSONResponse(content=out)


@app.get("/quiz/{quiz_id}")
async def get_quiz(quiz_id: int):
    db: Session = next(get_db())
    r = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Quiz not found")
    try:
        data = json.loads(r.full_quiz_data)
    except Exception:
        data = {"error": "failed to parse stored quiz data"}
    return JSONResponse(content={"id": r.id, "url": r.url, "title": r.title, "date_generated": r.date_generated.isoformat(), **data})


# Serve frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h3>Frontend not found. Put static frontend in /frontend directory.</h3>")
