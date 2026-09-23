import sys
import os
from pymongo.errors import CollectionInvalid

# Aggiunge il path della directory radice al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

def init_silver_schema(db):
    """
    Imposta le regole di validazione JSON Schema per la collection "silver_data".
    Garantisce la data governance (qualità del dato, conformità, aspetti estratti e lingua).
    """
    silver_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["original_text", "cleaned_text", "sentiment_score", "sentiment_label", "_governance"],
            "properties": {
                "original_text": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "cleaned_text": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "sentiment_score": {
                    "bsonType": "double",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "description": "must be a double in [-1.0, 1.0] and is required"
                },
                "sentiment_label": {
                    "enum": ["Positive", "Negative", "Neutral"],
                    "description": "must be 'Positive', 'Negative', or 'Neutral' and is required"
                },
                "language": {
                    "bsonType": "string",
                    "description": "detected language code (e.g. en, it, es)"
                },
                "aspects": {
                    "bsonType": "array",
                    "description": "topics or film aspects discussed (e.g. directing, acting, soundtrack)",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "_governance": {
                    "bsonType": "object",
                    "required": ["source_platform", "extraction_timestamp", "source_id"],
                    "properties": {
                        "source_platform": {
                            "enum": ["youtube", "letterboxd", "test"],
                            "description": "source of the data"
                        },
                        "extraction_timestamp": {
                            "bsonType": "string",
                            "description": "ISO timestamp of extraction"
                        },
                        "source_id": {
                            "bsonType": "string",
                            "description": "unique identifier in the source platform / bronze layer"
                        }
                    }
                }
            }
        }
    }

    try:
        db.create_collection("silver_data", validator=silver_schema)
        print("✅ Collection 'silver_data' creata con schema di validazione.")
    except CollectionInvalid:
        db.command({
            "collMod": "silver_data",
            "validator": silver_schema,
            "validationLevel": "strict"
        })
        print("✅ Schema di validazione aggiornato per 'silver_data'.")


def init_indexes(db):
    """
    Crea indici univoci e indici di supporto per garantire idempotenza,
    deduplicazione e query veloci sul livello Bronze e Silver.
    """
    # raw_youtube: comment_id univoco
    db["raw_youtube"].create_index([("comment_id", 1)], unique=True)
    db["raw_youtube"].create_index([("_governance.processed", 1)])
    print("✅ Indici creati per 'raw_youtube' (comment_id univoco, _governance.processed).")

    # raw_letterboxd: film + author univoco
    db["raw_letterboxd"].create_index([("film", 1), ("author", 1)], unique=True)
    db["raw_letterboxd"].create_index([("_governance.processed", 1)])
    print("✅ Indici creati per 'raw_letterboxd' (film + author univoco, _governance.processed).")

    # silver_data: source_platform + source_id univoco
    db["silver_data"].create_index([("_governance.source_platform", 1), ("_governance.source_id", 1)], unique=True)
    db["silver_data"].create_index([("aspects", 1)])
    db["silver_data"].create_index([("language", 1)])
    print("✅ Indici creati per 'silver_data' (lineage univoco, aspects, language).")


def main():
    db = get_sync_db()
    print("Inizializzazione database in corso...")
    
    # Creazione delle collezioni Bronze (raw data) se non esistono
    bronze_collections = ["raw_youtube", "raw_letterboxd"]
    for coll in bronze_collections:
        if coll not in db.list_collection_names():
            db.create_collection(coll)
            print(f"✅ Collection Bronze '{coll}' creata.")
            
    # Inizializzazione schema Silver
    init_silver_schema(db)
    
    # Inizializzazione indici per deduplicazione
    init_indexes(db)
    
    print("Inizializzazione completata.")

if __name__ == "__main__":
    main()

