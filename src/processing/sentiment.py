import os
import re
from datetime import datetime, timezone
from transformers import pipeline
import sys
from dotenv import load_dotenv
from langdetect import detect, DetectorFactory

# Fissa il seed per riproducibilità nel rilevamento della lingua
DetectorFactory.seed = 0

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

load_dotenv()

MODEL_NAME = os.getenv("TRANSFORMERS_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")

print(f"Caricamento del modello NLP: {MODEL_NAME}...")
try:
    sentiment_pipeline = pipeline("sentiment-analysis", model=MODEL_NAME, tokenizer=MODEL_NAME)
    print("Modello caricato con successo.")
except Exception as e:
    print(f"Errore nel caricamento del modello: {e}")
    sentiment_pipeline = None

# Vocabolario bilingue (IT/EN) per Aspect-Based Sentiment & Social Listening
ASPECT_KEYWORDS = {
    "directing": ["direct", "director", "regia", "regista", "direction", "filmmaker", "villeneuve", "nolan"],
    "acting": ["act", "acting", "actor", "actress", "recitazione", "attore", "attrice", "cast", "performance", "chalamet", "zendaya", "butler", "cage", "nicolas cage", "gleeson", "brendan gleeson"],
    "soundtrack": ["music", "soundtrack", "score", "colonna sonora", "musica", "audio", "sound", "zimmer"],
    "visuals": ["visual", "visuals", "cinematography", "cgi", "effects", "fotografia", "effetti", "estetica", "shot", "scenografia", "noir", "black and white", "bianco e nero", "color", "colori"],
    "plot": ["plot", "story", "trama", "sceneggiatura", "script", "ending", "finale", "pacing", "ritmo", "storia"]
}

def clean_text(text):
    """
    Pulisce il testo (rimuove URL, tag HTML, spazi multipli).
    """
    if not isinstance(text, str):
        return ""
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def detect_language(text):
    """
    Rileva automaticamente la lingua del commento (es. 'it', 'en', 'es').
    """
    if not text or len(text.strip()) < 4:
        return "unknown"
    try:
        return detect(text)
    except Exception:
        return "unknown"

def extract_aspects(text):
    """
    Estrae le categorie tematiche (aspects) menzionate nel commento/recensione.
    """
    text_lower = text.lower()
    detected_aspects = []
    
    for aspect, keywords in ASPECT_KEYWORDS.items():
        pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
        if re.search(pattern, text_lower):
            detected_aspects.append(aspect)
            
    return detected_aspects

def analyze_sentiment(text):
    """
    Analizza il sentiment e mappa l'output normalizzato tra -1.0 e 1.0.
    """
    if not sentiment_pipeline or not text:
        return 0.0, "Neutral"

    truncated_text = " ".join(text.split()[:100])
    
    try:
        result = sentiment_pipeline(truncated_text)[0]
        label = result['label'].lower()
        score = result['score']

        if "negative" in label or label == "label_0":
            mapped_label = "Negative"
            final_score = -score
        elif "positive" in label or label == "label_2":
            mapped_label = "Positive"
            final_score = score
        else:
            mapped_label = "Neutral"
            final_score = 0.0

        return float(final_score), mapped_label
    except Exception as e:
        print(f"Errore durante l'analisi: {e}")
        return 0.0, "Neutral"

def process_source_collection(db, collection_name, platform_name, id_extractor, batch_size=50):
    """
    Elabora i documenti non ancora processati da una collection Bronze specifica.
    Garantisce idempotenza, arricchimento (lingua, aspetti, sentiment) e data lineage.
    """
    raw_col = db[collection_name]
    silver_col = db["silver_data"]

    # Seleziona solo documenti ancora non processati
    cursor = raw_col.find({"_governance.processed": {"$ne": True}}).limit(batch_size)
    processed_count = 0

    for doc in cursor:
        original_text = doc.get("text", "")
        cleaned = clean_text(original_text)
        
        # 1. Rilevamento lingua
        lang = detect_language(cleaned)
        
        # 2. Estrazione aspetti tematici
        aspects = extract_aspects(cleaned)
        
        # 3. Sentiment Analysis
        score, label = analyze_sentiment(cleaned)
        
        source_id = id_extractor(doc)
        
        silver_doc = {
            "original_text": original_text,
            "cleaned_text": cleaned,
            "sentiment_score": score,
            "sentiment_label": label,
            "language": lang,
            "aspects": aspects,
            "_governance": {
                "source_platform": platform_name,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "source_id": str(source_id)
            }
        }
        
        # Upsert idempotente in Silver (garantito da indice univoco source_platform + source_id)
        silver_col.update_one(
            {
                "_governance.source_platform": platform_name,
                "_governance.source_id": str(source_id)
            },
            {"$set": silver_doc},
            upsert=True
        )

        # Marca il documento Bronze come processato con timestamp di audit
        raw_col.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "_governance.processed": True,
                    "_governance.processed_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        processed_count += 1

    return processed_count

def process_unprocessed_data(batch_size=100):
    """
    Coordina il processamento di tutte le fonti Bronze (YouTube e Letterboxd).
    Continua a ciclare a batch finché tutti i record non processati vengono elaborati.
    """
    db = get_sync_db()

    # YouTube: comment_id univoco
    total_yt = 0
    while True:
        yt_count = process_source_collection(
            db,
            collection_name="raw_youtube",
            platform_name="youtube",
            id_extractor=lambda doc: doc.get("comment_id", str(doc.get("_id"))),
            batch_size=batch_size
        )
        total_yt += yt_count
        if yt_count == 0:
            break
        print(f"Batch elaborato da YouTube -> Silver: {yt_count} documenti (totale finora: {total_yt}).")
    print(f"✅ Totale completato YouTube -> Silver: {total_yt} documenti.")

    # Letterboxd: film + author univoco
    total_lb = 0
    while True:
        lb_count = process_source_collection(
            db,
            collection_name="raw_letterboxd",
            platform_name="letterboxd",
            id_extractor=lambda doc: f"{doc.get('film', 'film')}#{doc.get('author', 'unknown')}",
            batch_size=batch_size
        )
        total_lb += lb_count
        if lb_count == 0:
            break
        print(f"Batch elaborato da Letterboxd -> Silver: {lb_count} documenti (totale finora: {total_lb}).")
    print(f"✅ Totale completato Letterboxd -> Silver: {total_lb} documenti.")

if __name__ == "__main__":
    process_unprocessed_data()
