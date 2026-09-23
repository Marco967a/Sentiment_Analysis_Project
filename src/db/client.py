import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()

# Recupera la URI e il nome del DB dalle variabili d'ambiente
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "sentiment_db")

def get_sync_db() -> Database:
    """
    Restituisce un'istanza sincrona del database (utile per script di inizializzazione).
    """
    client: MongoClient = MongoClient(MONGODB_URI)
    return client[MONGODB_DB_NAME]

class AsyncDatabase:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[Database] = None

    @classmethod
    def connect(cls):
        """Inizializza la connessione asincrona a MongoDB."""
        if cls.client is None:
            cls.client = AsyncIOMotorClient(MONGODB_URI)
            cls.db = cls.client[MONGODB_DB_NAME]
            print(f"Connected to MongoDB: {MONGODB_URI}")

    @classmethod
    def close(cls):
        """Chiude la connessione."""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("MongoDB connection closed.")

async def get_async_db():
    """Dipendenza FastAPI per ottenere il DB asincrono."""
    if AsyncDatabase.db is None:
        AsyncDatabase.connect()
    return AsyncDatabase.db

