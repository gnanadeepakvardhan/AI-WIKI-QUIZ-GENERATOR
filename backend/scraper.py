import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def is_wikipedia_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return "wikipedia.org" in p.netloc
    except Exception:
        return False


def scrape_wikipedia(url: str) -> dict:
    """Fetches the Wikipedia page and extracts title, summary, sections and cleaned text.

    Returns a dict: { title, summary, sections (list), clean_text }
    """
    if not is_wikipedia_url(url):
        raise ValueError("URL is not a Wikipedia URL")

    resp = requests.get(url, headers={"User-Agent": "ai-quiz-generator/1.0"}, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_tag = soup.find(id="firstHeading")
    title = title_tag.get_text(strip=True) if title_tag else soup.title.string if soup.title else ""

    # Main content
    content_div = soup.find(id="mw-content-text") or soup.find("body")

    # Remove references, sup tags, and tables
    for sup in content_div.find_all("sup"):
        sup.decompose()
    for table in content_div.find_all("table"):
        table.decompose()

    # Sections: headings inside content
    sections = []
    for header in content_div.find_all(["h2", "h3"]):
        span = header.find("span", class_="mw-headline")
        if span:
            sections.append(span.get_text(strip=True))

    # Extract paragraphs
    paragraphs = []
    for p in content_div.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            paragraphs.append(text)

    clean_text = "\n\n".join(paragraphs)
    summary = paragraphs[0] if paragraphs else ""

    return {
        "title": title,
        "summary": summary,
        "sections": sections,
        "clean_text": clean_text,
        "raw_html": resp.text,
    }
