import sys
import os
from pymongo.errors import CollectionInvalid

# Aggiunge il path della directory radice al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

def init_silver_schema(db):
    """
    Imposta le regole di validazione JSON Schema per la collection "silver_data".
    Garantisce la data governance.
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
                "_governance": {
                    "bsonType": "object",
                    "required": ["source_platform", "extraction_timestamp"],
                    "properties": {
                        "source_platform": {
                            "enum": ["youtube", "letterboxd", "test"],
                            "description": "source of the data"
                        },
                        "extraction_timestamp": {
                            "bsonType": "string",
                            "description": "ISO timestamp of extraction"
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
        # La collezione esiste già, applichiamo l'aggiornamento
        db.command({
            "collMod": "silver_data",
            "validator": silver_schema,
            "validationLevel": "strict"
        })
        print("✅ Schema di validazione aggiornato per 'silver_data'.")


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
    
    print("Inizializzazione completata.")

if __name__ == "__main__":
    main()

