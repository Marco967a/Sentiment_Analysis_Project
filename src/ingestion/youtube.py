import os
from googleapiclient.discovery import build
from datetime import datetime
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_comments(video_id, max_results=100):
    """
    Recupera i commenti da un video YouTube ordinandoli per rilevanza (spesso correlato ai like).
    """
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "your_youtube_api_key_here":
        print("ATTENZIONE: YOUTUBE_API_KEY non configurata in .env")
        return []

    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    comments_data = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance" # Ordina per i commenti più rilevanti/apprezzati
        )
        response = request.execute()

        for item in response.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]
            
            # Filtro opzionale: salva solo se ha almeno 1 like (da configurare a seconda delle esigenze)
            like_count = comment.get("likeCount", 0)
            
            comment_doc = {
                "video_id": video_id,
                "comment_id": item["id"],
                "author": comment.get("authorDisplayName", "Unknown"),
                "text": comment.get("textDisplay"),
                "like_count": like_count,
                "published_at": comment.get("publishedAt"),
                "_governance": {
                    "source_platform": "youtube",
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "api_version": "v3"
                }
            }
            comments_data.append(comment_doc)

    except Exception as e:
        print(f"Errore durante l'API call a YouTube: {e}")

    return comments_data

def save_to_bronze(comments):
    if not comments:
        print("Nessun commento da salvare (o API key mancante).")
        return
        
    db = get_sync_db()
    collection = db["raw_youtube"]
    
    # Per evitare duplicati (se si lancia lo script più volte)
    # in una pipeline reale useremmo update_one con upsert
    result = collection.insert_many(comments)
    print(f"Salvati {len(result.inserted_ids)} documenti in raw_youtube.")

if __name__ == "__main__":
    # Esempio: Trailer di un film o video di recensione
    test_video_id = "U2Qp5pL3ovA" # Esempio (Dune 2 Trailer)
    print(f"Recupero commenti per il video: {test_video_id}...")
    scraped_data = get_youtube_comments(test_video_id, max_results=50)
    print(f"Trovati {len(scraped_data)} commenti.")
    save_to_bronze(scraped_data)

