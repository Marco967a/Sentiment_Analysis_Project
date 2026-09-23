import os
import re
from datetime import datetime
from transformers import pipeline
import sys
from dotenv import load_dotenv

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

def clean_text(text):
    """
    Pulisce il testo (rimuove URL, tag HTML, spazi multipli).
    """
    if not isinstance(text, str):
        return ""
    # Rimuovi URL
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # Rimuovi tag HTML
    text = re.sub(r'<.*?>', '', text)
    # Rimuovi caratteri speciali mantenendo punteggiatura base
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    # Spazi multipli
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def analyze_sentiment(text):
    """
    Analizza il sentiment e mappa l'output di RoBERTa al formato richiesto dal DB.
    RoBERTa output: LABEL_0 (negative), LABEL_1 (neutral), LABEL_2 (positive)
    o 'negative', 'neutral', 'positive' a seconda del modello.
    """
    if not sentiment_pipeline or not text:
        return 0.0, "Neutral"

    # Trunca per limiti del modello (max 512 token)
    truncated_text = " ".join(text.split()[:100])
    
    try:
        result = sentiment_pipeline(truncated_text)[0]
        label = result['label'].lower()
        score = result['score']

        # Normalizza score tra -1.0 e 1.0
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

def process_unprocessed_data():
    """
    Legge dati grezzi non processati, li pulisce,
    applica sentiment analysis e li salva in silver_data rispettando lo schema.
    """
    db = get_sync_db()
    raw_col = db["raw_letterboxd"]
    silver_col = db["silver_data"]

    # Idealmente qui c'è una logica per prendere solo i documenti non ancora processati
    # Per semplicità, prendiamo gli ultimi 10
    cursor = raw_col.find().limit(10)
    
    silver_docs = []
    for doc in cursor:
        original_text = doc.get("text", "")
        cleaned = clean_text(original_text)
        
        score, label = analyze_sentiment(cleaned)
        
        silver_doc = {
            "original_text": original_text,
            "cleaned_text": cleaned,
            "sentiment_score": score,
            "sentiment_label": label,
            "_governance": {
                "source_platform": doc.get("_governance", {}).get("source_platform", "unknown"),
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
        }
        silver_docs.append(silver_doc)

    if silver_docs:
        result = silver_col.insert_many(silver_docs)
        print(f"Processati e salvati in Silver: {len(result.inserted_ids)} documenti.")
    else:
        print("Nessun documento da processare.")

if __name__ == "__main__":
    process_unprocessed_data()

