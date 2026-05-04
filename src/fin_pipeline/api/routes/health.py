from fastapi import APIRouter

from fin_pipeline.schemas.api import HealthResponse
from fin_pipeline.storage.qdrant_indexer import QdrantIndexer

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica o status do serviço e a conexão com o Qdrant."""

    qdrant_ok = False
    # Verifica a conexão com o Qdrant
    try:
        indexer = QdrantIndexer()
        qdrant_ok = indexer.collection_exists()
    except Exception:
        pass

    # Define o status geral com base na conexão com o Qdrant
    status = "ok" if qdrant_ok else "degraded"

    return HealthResponse(
        status=status,
        qdrant_connected=qdrant_ok,
    )