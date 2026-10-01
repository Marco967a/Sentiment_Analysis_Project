import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.db.client import get_sync_db
from src.logging_config import setup_logging

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_VIDEOS_FILE = Path(__file__).resolve().parents[2] / "config" / "youtube_videos.json"


class YouTubeQuotaExceeded(RuntimeError):
    """La quota giornaliera dell'API YouTube è esaurita: inutile proseguire con altri video."""


def get_api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key or key == "your_youtube_api_key_here":
        raise RuntimeError("YOUTUBE_API_KEY non configurata: impostala nel file .env.")
    return key


def _error_reason(error: HttpError) -> str:
    try:
        return json.loads(error.content.decode("utf-8"))["error"]["errors"][0]["reason"]
    except (ValueError, KeyError, IndexError, AttributeError):
        return ""


def get_youtube_comments(video_id: str, max_results: int = 100, video_title: Optional[str] = None) -> list[dict]:
    """
    Recupera i commenti top-level di un video, ordinati per rilevanza, con paginazione.
    Per i problemi del singolo video (inesistente, commenti disabilitati) restituisce quanto raccolto;
    solleva YouTubeQuotaExceeded se la quota è esaurita.
    """
    youtube = build("youtube", "v3", developerKey=get_api_key(), cache_discovery=False)
    comments: list[dict] = []
    page_token = None

    while len(comments) < max_results:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(100, max_results - len(comments)),
            order="relevance",
            pageToken=page_token,
        )
        try:
            response = request.execute()
        except HttpError as e:
            reason = _error_reason(e)
            if reason in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
                raise YouTubeQuotaExceeded(f"Quota API YouTube esaurita ({reason}).") from e
            if reason in ("commentsDisabled", "videoNotFound", "forbidden"):
                logger.warning("Video %s non utilizzabile (%s): saltato.", video_id, reason)
            else:
                logger.error("Errore API YouTube per il video %s (%s): %s", video_id, reason or "sconosciuto", e)
            break

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            text = snippet.get("textOriginal") or snippet.get("textDisplay")
            if not text:
                continue
            comments.append({
                "video_id": video_id,
                "video_title": video_title,
                "comment_id": item["id"],
                "author": snippet.get("authorDisplayName", "Unknown"),
                "text": text,
                "like_count": int(snippet.get("likeCount", 0)),
                "published_at": snippet.get("publishedAt"),
                "_governance": {
                    "source_platform": "youtube",
                    "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                    "api_version": "v3",
                },
            })
            if len(comments) >= max_results:
                break

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return comments


def save_to_bronze(comments: list[dict], db=None) -> tuple[int, int]:
    """Upsert idempotente in raw_youtube (preserva lo stato di elaborazione). Restituisce (nuovi, aggiornati)."""
    if not comments:
        logger.info("Nessun commento da salvare.")
        return 0, 0

    collection = (db if db is not None else get_sync_db())["raw_youtube"]
    inserted = updated = 0
    for c in comments:
        payload = {
            "video_id": c["video_id"],
            "author": c["author"],
            "text": c["text"],
            "like_count": c["like_count"],
            "published_at": c.get("published_at"),
            "_governance.source_platform": "youtube",
            "_governance.extraction_timestamp": c["_governance"]["extraction_timestamp"],
            "_governance.api_version": c["_governance"]["api_version"],
        }
        if c.get("video_title"):
            payload["video_title"] = c["video_title"]
        result = collection.update_one(
            {"comment_id": c["comment_id"]},
            {"$set": payload, "$setOnInsert": {"_governance.processed": False}},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count:
            updated += 1
    logger.info("Salvati in raw_youtube: %s nuovi, %s aggiornati su %s commenti.", inserted, updated, len(comments))
    return inserted, updated


def load_videos(videos_file: Path) -> list[dict]:
    with open(videos_file, encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[list[str]] = None) -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Ingestione commenti YouTube nel Bronze layer.")
    parser.add_argument("--videos-file", type=Path, default=DEFAULT_VIDEOS_FILE,
                        help="JSON con la lista [{'id': ..., 'title': ...}]")
    parser.add_argument("--video", action="append", help="ID video (ripetibile): ha la precedenza sul file")
    parser.add_argument("--max-results", type=int, default=100, help="commenti massimi per video")
    args = parser.parse_args(argv)

    videos = [{"id": v, "title": None} for v in args.video] if args.video else load_videos(args.videos_file)

    total = 0
    for video in videos:
        logger.info("Recupero commenti per: '%s' (ID: %s)...", video.get("title"), video["id"])
        try:
            comments = get_youtube_comments(video["id"], max_results=args.max_results, video_title=video.get("title"))
        except YouTubeQuotaExceeded as e:
            logger.error("%s Interrompo l'ingestione.", e)
            break
        logger.info("Trovati %s commenti.", len(comments))
        save_to_bronze(comments)
        total += len(comments)

    logger.info("Ingestione completata: %s commenti estratti nel Bronze layer.", total)


if __name__ == "__main__":
    main()
