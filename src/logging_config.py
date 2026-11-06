import logging
import os


def setup_logging() -> None:
    """Configura il logging di root; il livello si imposta con la variabile d'ambiente LOG_LEVEL."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
