import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()

def get_mongodb_uri() -> str:
    """Recupera la URI di MongoDB da env o da Streamlit secrets se disponibile."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "MONGODB_URI" in st.secrets:
                uri = st.secrets["MONGODB_URI"]
        except Exception:
            pass
    return uri or "mongodb://localhost:27017/"

def get_mongodb_name() -> str:
    """Recupera il nome del DB da env o da Streamlit secrets se disponibile."""
    db_name = os.getenv("MONGODB_DB_NAME")
    if not db_name:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "MONGODB_DB_NAME" in st.secrets:
                db_name = st.secrets["MONGODB_DB_NAME"]
        except Exception:
            pass
    return db_name or "sentiment_db"

def get_sync_db(timeout_ms: int = 5000) -> Database:
    """
    Restituisce un'istanza sincrona del database con timeout di selezione server configurabile.
    """
    client: MongoClient = MongoClient(get_mongodb_uri(), serverSelectionTimeoutMS=timeout_ms)
    return client[get_mongodb_name()]

class AsyncDatabase:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[Database] = None

    @classmethod
    def connect(cls, timeout_ms: int = 5000):
        """Inizializza la connessione asincrona a MongoDB."""
        if cls.client is None:
            uri = get_mongodb_uri()
            db_name = get_mongodb_name()
            cls.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=timeout_ms)
            cls.db = cls.client[db_name]
            print(f"Connected to MongoDB: {uri}")

    @classmethod
    def close(cls):
        """Chiude la connessione."""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("MongoDB connection closed.")

async def get_async_db():
    """Restituisce il client DB asincrono."""
    if AsyncDatabase.db is None:
        AsyncDatabase.connect()
    return AsyncDatabase.db

