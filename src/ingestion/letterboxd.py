import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

def scrape_letterboxd_reviews(film_slug, max_pages=1):
    """
    Scrape base per le recensioni di un film su Letterboxd.
    film_slug: es. 'the-matrix' o 'dune-part-two'
    """
    base_url = f"https://letterboxd.com/film/{film_slug}/reviews/by/activity/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    reviews_data = []

    for page in range(1, max_pages + 1):
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Errore nel recupero della pagina {page}: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Le recensioni possono essere article con classe 'production-viewing' o tag con classe 'film-detail'
        review_items = soup.find_all('article', class_='production-viewing')
        if not review_items:
            review_items = soup.find_all('li', class_='film-detail')

        for item in review_items:
            review_text_div = item.find('div', class_='js-review-body') or item.find('div', class_='body-text')
            if not review_text_div:
                continue
                
            text = review_text_div.get_text(separator=' ', strip=True)
            
            author_tag = item.find('span', class_='owner') or item.find('a', class_='name')
            author = author_tag.get_text().strip() if author_tag else "Unknown"

            # Rating in stars
            rating_tag = item.find('span', class_='inline-rating') or item.find('span', class_='rating')
            rating = rating_tag.get_text().strip() if rating_tag else None

            review_doc = {
                "film": film_slug,
                "author": author,
                "rating": rating,
                "text": text,
                "_governance": {
                    "source_platform": "letterboxd",
                    "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                    "raw_url": url
                }
            }
            reviews_data.append(review_doc)

    return reviews_data

def save_to_bronze(reviews):
    if not reviews:
        print("Nessuna recensione da salvare.")
        return
        
    db = get_sync_db()
    collection = db["raw_letterboxd"]
    
    upserted_count = 0
    modified_count = 0
    for review in reviews:
        res = collection.update_one(
            {"film": review["film"], "author": review["author"]},
            {
                "$set": {
                    "film": review["film"],
                    "author": review["author"],
                    "rating": review["rating"],
                    "text": review["text"],
                    "_governance.source_platform": "letterboxd",
                    "_governance.extraction_timestamp": review["_governance"]["extraction_timestamp"],
                    "_governance.raw_url": review["_governance"]["raw_url"]
                },
                "$setOnInsert": {
                    "_governance.processed": False
                }
            },
            upsert=True
        )
        if res.upserted_id:
            upserted_count += 1
        elif res.modified_count:
            modified_count += 1
            
    print(f"Salvati in raw_letterboxd: {upserted_count} nuovi, {modified_count} aggiornati su {len(reviews)} recensioni.")

if __name__ == "__main__":
    film = "dune-part-two"
    print(f"Scraping reviews per il film: {film}...")
    scraped_data = scrape_letterboxd_reviews(film, max_pages=1)
    print(f"Trovate {len(scraped_data)} recensioni.")
    save_to_bronze(scraped_data)

