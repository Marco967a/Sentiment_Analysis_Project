import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

logger = logging.getLogger(__name__)


def _get_setting(name: str, default: str) -> str:
    """Legge un parametro da variabile d'ambiente o, in alternativa, da Streamlit secrets."""
    value = os.getenv(name)
    if not value:
        try:
            import streamlit as st
            if name in st.secrets:
                value = st.secrets[name]
        except Exception:
            pass
    return value or default


def get_mongodb_uri() -> str:
    """Recupera la URI di MongoDB da env o da Streamlit secrets se disponibile."""
    return _get_setting("MONGODB_URI", "mongodb://localhost:27017/")


def get_mongodb_name() -> str:
    """Recupera il nome del DB da env o da Streamlit secrets se disponibile."""
    return _get_setting("MONGODB_DB_NAME", "sentiment_db")


@lru_cache(maxsize=None)
def _get_client(uri: str, timeout_ms: int) -> MongoClient:
    # Un solo MongoClient per (uri, timeout): ha un pool interno ed è thread-safe.
    # Non loggare mai l'URI completo: può contenere le credenziali.
    logger.info("Connessione a MongoDB: %s", uri.rsplit("@", 1)[-1])
    return MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)


def get_sync_db(timeout_ms: int = 5000) -> Database:
    """Restituisce il database sincrono riutilizzando il client condiviso del processo."""
    return _get_client(get_mongodb_uri(), timeout_ms)[get_mongodb_name()]
