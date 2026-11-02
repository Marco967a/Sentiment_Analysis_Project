import logging

from pymongo.errors import OperationFailure

from src.db.client import get_sync_db
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)

INT_TYPES = ["int", "long"]

_BRONZE_GOVERNANCE = {
    "bsonType": "object",
    "required": ["source_platform", "extraction_timestamp"],
    "properties": {
        "source_platform": {"enum": ["youtube", "letterboxd"]},
        "extraction_timestamp": {"bsonType": "string"},
        "processed": {"bsonType": "bool"},
        "processed_at": {"bsonType": "string"},
        "attempts": {"bsonType": INT_TYPES, "description": "tentativi di elaborazione falliti"},
        "error": {"bsonType": "string", "description": "ultimo errore di elaborazione"},
    },
}


def _bronze_schema(required: list[str], extra_properties: dict) -> dict:
    governance = dict(_BRONZE_GOVERNANCE)
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": required + ["_governance"],
            "properties": {
                "text": {"bsonType": "string"},
                **extra_properties,
                "_governance": governance,
            },
        }
    }


RAW_YOUTUBE_SCHEMA = _bronze_schema(
    ["comment_id", "video_id", "text"],
    {
        "comment_id": {"bsonType": "string"},
        "video_id": {"bsonType": "string"},
        "like_count": {"bsonType": INT_TYPES, "minimum": 0},
    },
)

RAW_LETTERBOXD_SCHEMA = _bronze_schema(
    ["film", "author", "text"],
    {
        "film": {"bsonType": "string"},
        "author": {"bsonType": "string"},
        "review_id": {"bsonType": "string"},
        "rating": {"bsonType": ["double", "int", "null"], "minimum": 0.5, "maximum": 5.0},
    },
)

SILVER_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["original_text", "cleaned_text", "sentiment_score", "sentiment_label", "_governance"],
        "properties": {
            "original_text": {"bsonType": "string"},
            "cleaned_text": {"bsonType": "string"},
            "sentiment_score": {"bsonType": "double", "minimum": -1.0, "maximum": 1.0},
            "sentiment_label": {"enum": ["Positive", "Negative", "Neutral"]},
            "language": {"bsonType": "string", "description": "codice lingua rilevato (en, it, es, unknown)"},
            "aspects": {"bsonType": "array", "items": {"bsonType": "string"}},
            "aspect_sentiments": {
                "bsonType": "array",
                "description": "sentiment della frase in cui compare ciascun aspetto",
                "items": {
                    "bsonType": "object",
                    "required": ["aspect", "sentiment_score", "sentiment_label"],
                    "properties": {
                        "aspect": {"bsonType": "string"},
                        "sentiment_score": {"bsonType": "double", "minimum": -1.0, "maximum": 1.0},
                        "sentiment_label": {"enum": ["Positive", "Negative", "Neutral"]},
                        "sentence": {"bsonType": "string"},
                    },
                },
            },
            "published_at": {"bsonType": ["string", "null"], "description": "data originale del contenuto (ISO)"},
            "model_name": {"bsonType": "string", "description": "modello NLP che ha prodotto il sentiment"},
            "cleaning_version": {"bsonType": INT_TYPES},
            "_governance": {
                "bsonType": "object",
                "required": ["source_platform", "extraction_timestamp", "source_id"],
                "properties": {
                    "source_platform": {"enum": ["youtube", "letterboxd", "test"]},
                    "extraction_timestamp": {"bsonType": "string"},
                    "source_id": {"bsonType": "string"},
                },
            },
        },
    }
}


def apply_validator(db, name: str, schema: dict, level: str) -> None:
    """Crea la collection con validatore, oppure aggiorna il validatore se esiste già (idempotente)."""
    if name in db.list_collection_names():
        db.command({"collMod": name, "validator": schema, "validationLevel": level, "validationAction": "error"})
        logger.info("Validatore aggiornato per '%s' (level=%s).", name, level)
    else:
        db.create_collection(name, validator=schema, validationLevel=level, validationAction="error")
        logger.info("Collection '%s' creata con validatore (level=%s).", name, level)


def init_schemas(db) -> None:
    # Bronze: "moderate" non rifiuta aggiornamenti su documenti storici già non conformi.
    apply_validator(db, "raw_youtube", RAW_YOUTUBE_SCHEMA, "moderate")
    apply_validator(db, "raw_letterboxd", RAW_LETTERBOXD_SCHEMA, "moderate")
    apply_validator(db, "silver_data", SILVER_SCHEMA, "strict")


def init_indexes(db) -> None:
    """Crea gli indici univoci e di supporto (idempotente: create_index non fa nulla se già presente)."""
    raw_yt = db["raw_youtube"]
    raw_yt.create_index([("comment_id", 1)], unique=True)
    raw_yt.create_index([("_governance.processed", 1)])

    raw_lb = db["raw_letterboxd"]
    # Il vecchio indice (film, author) impediva più recensioni dello stesso autore (es. rewatch)
    # e faceva collidere gli autori "Unknown": viene sostituito da (film, review_id).
    try:
        raw_lb.drop_index("film_1_author_1")
        logger.info("Rimosso il vecchio indice univoco 'film_1_author_1' su raw_letterboxd.")
    except OperationFailure:
        pass
    raw_lb.create_index(
        [("film", 1), ("review_id", 1)],
        unique=True,
        partialFilterExpression={"review_id": {"$type": "string"}},
    )
    raw_lb.create_index([("_governance.processed", 1)])

    silver = db["silver_data"]
    silver.create_index(
        [("_governance.source_platform", 1), ("_governance.source_id", 1)], unique=True
    )
    silver.create_index([("aspects", 1)])
    silver.create_index([("language", 1)])
    silver.create_index([("published_at", -1)])
    logger.info("Indici verificati/creati su raw_youtube, raw_letterboxd, silver_data.")


def init_database(db) -> None:
    init_schemas(db)
    init_indexes(db)


def main() -> None:
    setup_logging()
    logger.info("Inizializzazione database in corso...")
    init_database(get_sync_db())
    logger.info("Inizializzazione completata.")


if __name__ == "__main__":
    main()
