import argparse
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.db.client import get_sync_db
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)
REQUEST_TIMEOUT = (5, 20)  # (connect, read) in secondi
PAGE_DELAY_SECONDS = 1.0

_PERMALINK_RE = re.compile(r"^/[^/]+/film/[^/]+/(?:\d+/)?$")
_RATED_CLASS_RE = re.compile(r"rated-(\d+)")


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def parse_rating(tag) -> Optional[float]:
    """Converte il rating Letterboxd in un numero 0.5-5.0 (None se assente o non valido)."""
    if tag is None:
        return None
    for css_class in tag.get("class", []):
        match = _RATED_CLASS_RE.fullmatch(css_class)
        if match:  # la classe 'rated-N' codifica le mezze stelle: N = stelle * 2
            return int(match.group(1)) / 2
    text = tag.get_text().strip()
    stars = text.count("★") + (0.5 if "½" in text else 0.0)
    return stars if 0.5 <= stars <= 5.0 else None


def extract_review_id(item, author: Optional[str]) -> Optional[str]:
    """
    Identificativo stabile della recensione: data-object-id, altrimenti il permalink,
    altrimenti l'autore (se noto). None se non è possibile identificarla in modo univoco.
    """
    object_id = item.get("data-object-id")
    if object_id:
        return str(object_id)
    for link in item.find_all("a", href=True):
        if _PERMALINK_RE.match(link["href"]):
            return link["href"]
    return author


def parse_reviews(html: bytes | str, film_slug: str, url: str) -> list[dict]:
    """Estrae le recensioni da una pagina HTML. Scarta quelle senza testo o senza identificativo."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("article", class_="production-viewing") or soup.find_all("li", class_="film-detail")

    reviews = []
    for item in items:
        body = item.find("div", class_="js-review-body") or item.find("div", class_="body-text")
        if not body:
            continue
        text = body.get_text(separator=" ", strip=True)
        if not text:
            continue

        author_tag = item.find("span", class_="owner") or item.find("a", class_="name")
        author = author_tag.get_text().strip() if author_tag else None
        review_id = extract_review_id(item, author)
        if not review_id:
            logger.warning("Recensione scartata: nessun identificativo né autore (%s).", url)
            continue

        rating_tag = item.find("span", class_="inline-rating") or item.find("span", class_="rating")
        time_tag = item.find("time")
        reviews.append({
            "film": film_slug,
            "review_id": review_id,
            "author": author or "Unknown",
            "rating": parse_rating(rating_tag),
            "text": text,
            "published_at": time_tag.get("datetime") if time_tag else None,
            "_governance": {
                "source_platform": "letterboxd",
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_url": url,
            },
        })
    return reviews


def scrape_letterboxd_reviews(film_slug: str, max_pages: int = 1) -> list[dict]:
    """Scrape base per le recensioni di un film su Letterboxd (es. 'the-matrix', 'dune-part-two')."""
    base_url = f"https://letterboxd.com/film/{film_slug}/reviews/by/activity/"
    session = _build_session()
    reviews: list[dict] = []

    for page in range(1, max_pages + 1):
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Errore nel recupero della pagina %s di '%s': %s", page, film_slug, e)
            break

        page_reviews = parse_reviews(response.content, film_slug, url)
        if not page_reviews:
            logger.info("Nessuna recensione alla pagina %s: fine della paginazione.", page)
            break
        reviews.extend(page_reviews)
        if page < max_pages:
            time.sleep(PAGE_DELAY_SECONDS)

    return reviews


def save_to_bronze(reviews: list[dict], db=None) -> tuple[int, int]:
    """Upsert idempotente in raw_letterboxd. Restituisce (nuovi, aggiornati)."""
    if not reviews:
        logger.info("Nessuna recensione da salvare.")
        return 0, 0

    collection = (db if db is not None else get_sync_db())["raw_letterboxd"]
    inserted = updated = 0
    for r in reviews:
        result = collection.update_one(
            {"film": r["film"], "review_id": r["review_id"]},
            {
                "$set": {
                    "film": r["film"],
                    "review_id": r["review_id"],
                    "author": r["author"],
                    "rating": r["rating"],
                    "text": r["text"],
                    "published_at": r["published_at"],
                    "_governance.source_platform": "letterboxd",
                    "_governance.extraction_timestamp": r["_governance"]["extraction_timestamp"],
                    "_governance.raw_url": r["_governance"]["raw_url"],
                },
                "$setOnInsert": {"_governance.processed": False},
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count:
            updated += 1
    logger.info("Salvati in raw_letterboxd: %s nuovi, %s aggiornati su %s recensioni.", inserted, updated, len(reviews))
    return inserted, updated


def main(argv: Optional[list[str]] = None) -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Ingestione recensioni Letterboxd nel Bronze layer.")
    parser.add_argument("--film", nargs="+", default=["dune-part-two"], help="slug dei film (es. the-matrix)")
    parser.add_argument("--pages", type=int, default=1, help="numero massimo di pagine per film")
    args = parser.parse_args(argv)

    for film in args.film:
        logger.info("Scraping recensioni per il film: %s...", film)
        scraped = scrape_letterboxd_reviews(film, max_pages=args.pages)
        logger.info("Trovate %s recensioni.", len(scraped))
        save_to_bronze(scraped)


if __name__ == "__main__":
    main()
