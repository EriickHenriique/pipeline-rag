from langfuse import Langfuse, get_client
from loguru import logger

from fin_pipeline.config import get_settings

_initialized = False


def init_langfuse() -> bool:
    """Initialize the Langfuse singleton. Safe to call multiple times; only initializes once."""
    global _initialized
    if _initialized:
        return True

    settings = get_settings()
    if not settings.langfuse_enabled or not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse desativado ou chaves ausentes. Rastreamento desativado.")
        return False

    Langfuse(
        public_key=settings.langfuse_public_key.get_secret_value(),
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        base_url=settings.langfuse_host,
    )
    _initialized = True
    logger.info("Langfuse inicializado.")
    return True


def is_tracing_enabled() -> bool:
    return _initialized
