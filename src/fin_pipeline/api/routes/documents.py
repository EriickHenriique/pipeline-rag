from fastapi import APIRouter, HTTPException, status
from loguru import logger

from fin_pipeline.schemas.api import DocumentInfo
from fin_pipeline.storage.qdrant_indexer import QdrantIndexer

router = APIRouter()

@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    """Retorna uma lista de documentos financeiros disponíveis no índice, agrupados por empresa, ano fiscal, trimestre e tipo de relatório.
    O endpoint consulta o Qdrant para obter os documentos indexados e retorna informações resumidas sobre cada documento, incluindo o número de chunks associados a ele.
    """
    try:
        indexer = QdrantIndexer()

        # Scroll para obter os primeiros 10.000 pontos (ajuste o limite conforme necessário)
        all_points, _ = indexer.client.scroll(
            collection_name=indexer.collection,
            with_payload=True,
            limit=10_000,
        )

    except Exception as e:
        logger.error(f"[GET /documents] Erro no Qdrant: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conexão com o serviço de armazenamento indisponível",
        )
    
    # Agrupa os pontos por empresa, ano fiscal, trimestre e tipo de relatório
    docs: dict[tuple, dict] = {}
    for point in all_points:
        p = point.payload
        key = (
            p["nome_empresa"],
            p["ano_fiscal"],
            p["trimestre"],
            p["tipo_relatorio"],
        )
        if key not in docs:
            docs[key] = {
                "nome_empresa": p["nome_empresa"],
                "ano_fiscal": p["ano_fiscal"],
                "trimestre": p["trimestre"],
                "tipo_relatorio": p["tipo_relatorio"],
                "chunk_count": 0,
            }
        docs[key]["chunk_count"] += 1

    return [DocumentInfo(**v) for v in docs.values()]