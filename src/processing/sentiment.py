import argparse
import html
import logging
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

import yaml
from dotenv import load_dotenv
from langdetect import DetectorFactory, detect

from src.db.client import get_sync_db
from src.logging_config import setup_logging

# Fissa il seed per riproducibilità nel rilevamento della lingua
DetectorFactory.seed = 0

load_dotenv()

logger = logging.getLogger(__name__)

# Routing per lingua: il modello inglese è il più accurato su 'en' ma fallisce sull'italiano (vedi
# scripts/benchmark_models.py); tutte le altre lingue usano il modello multilingue.
MODEL_EN = os.getenv("TRANSFORMERS_MODEL_EN", "cardiffnlp/twitter-roberta-base-sentiment-latest")
MODEL_MULTI = os.getenv("TRANSFORMERS_MODEL_MULTI", "cardiffnlp/twitter-xlm-roberta-base-sentiment")
ASPECTS_CONFIG = Path(os.getenv("ASPECTS_CONFIG", Path(__file__).resolve().parents[2] / "config" / "aspects.yaml"))

# Versione della logica di pulizia/estrazione: incrementarla quando clean_text o aspects.yaml cambiano,
# poi usare --reprocess-outdated per riallineare i record Silver esistenti.
CLEANING_VERSION = 5
MAX_ATTEMPTS = 3  # dopo N fallimenti un documento Bronze non viene più ritentato (vedi --retry-failed)


def select_model(language: str) -> str:
    """Modello di sentiment per la lingua rilevata: inglese -> MODEL_EN, altrimenti MODEL_MULTI."""
    return MODEL_EN if language == "en" else MODEL_MULTI


@lru_cache(maxsize=2)
def get_sentiment_pipeline(model_name: str = MODEL_EN):
    """Carica il modello NLP alla prima richiesta (nessun effetto collaterale all'import). None se non disponibile."""
    try:
        from transformers import pipeline
    except ImportError:
        logger.error("'transformers'/'torch' non installati: installa requirements-nlp.txt.")
        return None
    logger.info("Caricamento del modello NLP: %s...", model_name)
    try:
        model = pipeline("sentiment-analysis", model=model_name, tokenizer=model_name)
    except Exception:
        logger.exception("Errore nel caricamento del modello %s.", model_name)
        return None
    logger.info("Modello caricato con successo.")
    return model


def _compile_keywords(keywords) -> Optional[re.Pattern]:
    if not keywords:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(k.lower()) for k in keywords) + r")\b")


@lru_cache(maxsize=1)
def _aspect_patterns() -> dict[str, tuple[Optional[re.Pattern], Optional[re.Pattern]]]:
    """Per ogni aspetto: (pattern delle parole chiave, pattern delle parole chiave valide solo con un'opinione)."""
    with open(ASPECTS_CONFIG, encoding="utf-8") as f:
        vocabulary = yaml.safe_load(f)
    patterns = {}
    for aspect, entry in vocabulary.items():
        if isinstance(entry, list):
            entry = {"keywords": entry}
        patterns[aspect] = (_compile_keywords(entry.get("keywords")), _compile_keywords(entry.get("opinion_only")))
    return patterns


def _pipelines_available() -> bool:
    return all(get_sentiment_pipeline(name) is not None for name in (MODEL_EN, MODEL_MULTI))


_TYPOGRAPHIC = str.maketrans({
    "’": "'", "‘": "'", "ʼ": "'", "´": "'", "`": "'",
    "“": '"', "”": '"', "«": '"', "»": '"',
    "–": "-", "—": "-",
})


def clean_text(text) -> str:
    """
    Pulisce il testo (rimuove tag HTML, URL, spazi multipli).
    I tag vanno rimossi prima degli URL: altrimenti la regex degli URL consuma il `>` di
    `<a href="...">` e la regex dei tag cancella testo reale fino al `>` successivo.
    """
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<[^>]*>', ' ', text)
    text = html.unescape(text)
    # Apostrofi, virgolette e trattini tipografici (frequenti nei commenti) vanno normalizzati: altrimenti
    # la regex sotto li cancella e fonde le parole ("l’ora" -> "lora").
    text = text.translate(_TYPOGRAPHIC)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def detect_language(text: str) -> str:
    """Rileva automaticamente la lingua del commento (es. 'it', 'en', 'es')."""
    if not text or len(text.strip()) < 4:
        return "unknown"
    try:
        return detect(text)
    except Exception:
        return "unknown"


def extract_aspects(text: str, include_opinion_only: bool = True) -> list[str]:
    """
    Estrae le categorie tematiche (aspects) menzionate nel commento/recensione.
    Con include_opinion_only=False ignora le parole chiave ambigue (`opinion_only` in aspects.yaml).
    """
    text_lower = text.lower()
    found = []
    for aspect, (strong, weak) in _aspect_patterns().items():
        if (strong and strong.search(text_lower)) or (include_opinion_only and weak and weak.search(text_lower)):
            found.append(aspect)
    return found


# Connettivi che di solito introducono un giudizio opposto: ogni parte viene valutata a parte.
_CONTRAST = re.compile(
    r"\b(?:ma|però|pero|tuttavia|anche se|nonostante|but|however|although|though|whereas)\b", re.IGNORECASE
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# "La colonna sonora, però, è pessima": il connettivo tra virgole è una parentesi, non separa due giudizi.
_PARENTHETICAL = re.compile(r",\s*(?:però|pero|tuttavia|however|though)\s*,", re.IGNORECASE)


def split_clauses(text: str) -> list[str]:
    """Divide il testo in frasi e, dentro ogni frase, nei punti di contrasto ("ma", "but", ...)."""
    clauses = []
    for sentence in _SENTENCE_END.split(" ".join(_PARENTHETICAL.sub(" ", text).split())):
        for part in _CONTRAST.split(sentence):
            part = part.strip(" ,;-")
            if part:
                clauses.append(part)
    return clauses


def analyze_aspects(text: str, model_name: str, overall: tuple[float, str]) -> Optional[list[dict]]:
    """
    Sentiment per aspetto: ogni aspetto prende il sentiment della frase/clausola in cui compare,
    non quello dell'intero commento. Restituisce None se l'analisi di una clausola fallisce.
    Un testo senza divisioni riusa il sentiment complessivo (nessuna inferenza aggiuntiva).
    """
    clauses = split_clauses(text)
    if len(clauses) <= 1:
        clauses = [text]
    results = []
    for clause in clauses:
        candidates = extract_aspects(clause)
        if not candidates:
            continue
        sentiment = overall if clause == text else analyze_sentiment(clause, model_name)
        if sentiment is None:
            return None
        score, label = sentiment
        # Le parole chiave ambigue contano solo se la frase esprime un'opinione.
        aspects = candidates if label != "Neutral" else extract_aspects(clause, include_opinion_only=False)
        results.extend(
            {"aspect": a, "sentiment_score": score, "sentiment_label": label, "sentence": clause} for a in aspects
        )
    return results


def analyze_sentiment(text: str, model_name: str = MODEL_EN) -> Optional[tuple[float, str]]:
    """
    Analizza il sentiment e mappa l'output normalizzato tra -1.0 e 1.0.
    Restituisce None se l'analisi non è possibile: il chiamante non deve scrivere un
    risultato fittizio né marcare il documento come processato.
    """
    if not text:
        return 0.0, "Neutral"
    model = get_sentiment_pipeline(model_name)
    if model is None:
        return None

    try:
        result = model(text, truncation=True, max_length=512)[0]
    except Exception:
        logger.exception("Errore durante l'analisi del sentiment.")
        return None

    label = result["label"].lower()
    score = result["score"]
    if "negative" in label or label == "label_0":
        return float(-score), "Negative"
    if "positive" in label or label == "label_2":
        return float(score), "Positive"
    return 0.0, "Neutral"


def enrich(original_text: str) -> Optional[dict]:
    """Campi derivati di Silver (testo pulito, lingua, aspetti, sentiment, versioni). None se il sentiment fallisce."""
    cleaned = clean_text(original_text)
    language = detect_language(cleaned)
    model_name = select_model(language)
    sentiment = analyze_sentiment(cleaned, model_name)
    if sentiment is None:
        return None
    score, label = sentiment
    aspect_sentiments = analyze_aspects(cleaned, model_name, sentiment)
    if aspect_sentiments is None:
        return None
    return {
        "cleaned_text": cleaned,
        "sentiment_score": score,
        "sentiment_label": label,
        "language": language,
        "aspects": list(dict.fromkeys(a["aspect"] for a in aspect_sentiments)),
        "aspect_sentiments": aspect_sentiments,
        "model_name": model_name,
        "cleaning_version": CLEANING_VERSION,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_failure(raw_col, doc_id, reason: str) -> None:
    raw_col.update_one(
        {"_id": doc_id},
        {"$inc": {"_governance.attempts": 1}, "$set": {"_governance.error": reason[:500]}},
    )


def process_source_collection(
    db,
    collection_name: str,
    platform_name: str,
    id_extractor: Callable[[dict], str],
    batch_size: int = 50,
    failed_ids: Optional[set] = None,
) -> tuple[int, int]:
    """
    Elabora i documenti Bronze non ancora processati (idempotente, con data lineage).
    Un documento che fallisce resta non processato, con tentativo ed errore registrati nel Bronze;
    dopo MAX_ATTEMPTS fallimenti non viene più ritentato. Restituisce (elaborati, letti).
    """
    failed_ids = failed_ids if failed_ids is not None else set()
    raw_col = db[collection_name]
    silver_col = db["silver_data"]

    query = {
        "_governance.processed": {"$ne": True},
        "_governance.attempts": {"$not": {"$gte": MAX_ATTEMPTS}},
        "_id": {"$nin": list(failed_ids)},
    }
    processed_count = 0
    seen_count = 0

    for doc in raw_col.find(query).limit(batch_size):
        seen_count += 1
        try:
            original_text = doc.get("text") or ""
            fields = enrich(original_text)
            if fields is None:
                raise RuntimeError("analisi del sentiment non riuscita")
            source_id = str(id_extractor(doc))

            silver_doc = {
                "original_text": original_text,
                "published_at": doc.get("published_at"),
                **fields,
                "_governance.source_platform": platform_name,
                "_governance.source_id": source_id,
                "_governance.extraction_timestamp": doc.get("_governance", {}).get("extraction_timestamp") or _now(),
                "_governance.processed_at": _now(),
            }
            # Upsert idempotente (indice univoco source_platform + source_id)
            silver_col.update_one(
                {"_governance.source_platform": platform_name, "_governance.source_id": source_id},
                {"$set": silver_doc},
                upsert=True,
            )
            raw_col.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"_governance.processed": True, "_governance.processed_at": _now()},
                    "$unset": {"_governance.error": ""},
                },
            )
            processed_count += 1
        except Exception as e:
            logger.warning("Documento %s/%s non elaborato: %s", collection_name, doc["_id"], e)
            failed_ids.add(doc["_id"])
            _record_failure(raw_col, doc["_id"], f"{type(e).__name__}: {e}")

    return processed_count, seen_count


def _process_until_empty(db, label: str, **kwargs) -> int:
    total = 0
    failed_ids: set = set()
    while True:
        processed, seen = process_source_collection(db, failed_ids=failed_ids, **kwargs)
        total += processed
        if seen == 0:
            break
        logger.info("Batch %s -> Silver: %s/%s documenti (totale finora: %s).", label, processed, seen, total)
    if failed_ids:
        logger.warning("%s: %s documenti non elaborati (vedi _governance.error nel Bronze).", label, len(failed_ids))
    logger.info("Completato %s -> Silver: %s documenti.", label, total)
    return total


def process_unprocessed_data(batch_size: int = 100, db=None) -> None:
    """Coordina il processamento di tutte le fonti Bronze (YouTube e Letterboxd) a batch."""
    if not _pipelines_available():
        raise RuntimeError(
            "Pipeline NLP non disponibile: installa 'requirements-nlp.txt' e verifica i modelli. "
            "Nessun documento è stato modificato."
        )
    db = db if db is not None else get_sync_db()

    _process_until_empty(
        db, "YouTube",
        collection_name="raw_youtube",
        platform_name="youtube",
        id_extractor=lambda doc: doc.get("comment_id") or doc["_id"],
        batch_size=batch_size,
    )
    _process_until_empty(
        db, "Letterboxd",
        collection_name="raw_letterboxd",
        platform_name="letterboxd",
        # I documenti storici senza review_id usano l'autore, come prima.
        id_extractor=lambda doc: f"{doc.get('film', 'film')}#{doc.get('review_id') or doc.get('author', 'unknown')}",
        batch_size=batch_size,
    )


def reprocess_outdated_silver(db, batch_size: int = 100) -> int:
    """Riesegue l'arricchimento sui record Silver prodotti con un modello o una versione di pulizia obsoleti."""
    if not _pipelines_available():
        raise RuntimeError("Pipeline NLP non disponibile: nessun record Silver è stato modificato.")
    silver_col = db["silver_data"]
    query = {
        "$or": [
            {"language": "en", "model_name": {"$ne": MODEL_EN}},
            {"language": {"$ne": "en"}, "model_name": {"$ne": MODEL_MULTI}},
            {"cleaning_version": {"$not": {"$gte": CLEANING_VERSION}}},
        ]
    }
    updated = 0
    failed_ids: set = set()
    while True:
        batch = list(silver_col.find({**query, "_id": {"$nin": list(failed_ids)}}).limit(batch_size))
        if not batch:
            break
        for doc in batch:
            fields = enrich(doc.get("original_text") or "")
            if fields is None:
                failed_ids.add(doc["_id"])
                continue
            silver_col.update_one(
                {"_id": doc["_id"]},
                {"$set": {**fields, "_governance.processed_at": _now()}},
            )
            updated += 1
    logger.info("Riprocessati %s record Silver obsoleti (%s falliti).", updated, len(failed_ids))
    return updated


def reset_failed(db) -> int:
    """Azzera tentativi ed errori sui documenti Bronze, così vengono ritentati."""
    reset = 0
    for name in ("raw_youtube", "raw_letterboxd"):
        res = db[name].update_many(
            {"_governance.attempts": {"$exists": True}, "_governance.processed": {"$ne": True}},
            {"$unset": {"_governance.attempts": "", "_governance.error": ""}},
        )
        reset += res.modified_count
    logger.info("Azzerati i tentativi su %s documenti Bronze.", reset)
    return reset


def main(argv: Optional[list[str]] = None) -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Pipeline NLP Bronze -> Silver.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--retry-failed", action="store_true", help="azzera i tentativi falliti prima di elaborare")
    parser.add_argument("--reprocess-outdated", action="store_true",
                        help="riesegue l'arricchimento sui record Silver con modello/versione obsoleti")
    args = parser.parse_args(argv)

    db = get_sync_db()
    if args.retry_failed:
        reset_failed(db)
    process_unprocessed_data(batch_size=args.batch_size, db=db)
    if args.reprocess_outdated:
        reprocess_outdated_silver(db, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
