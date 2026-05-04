from fastapi import APIRouter, HTTPException, status
from loguru import logger
import time

from fin_pipeline.graph import run_query
from fin_pipeline.schemas.api import ErrorResponse, KPIResponse, QueryRequest, QueryResponse, SourceResponse


router = APIRouter()

@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Erro ao fazer a requisição"},
        500: {"model": ErrorResponse, "description": "Erro no Pipeline"},
        }
)

async def query_documents(request: QueryRequest) -> QueryResponse:
    """Executa uma consulta usando o pipeline RAG para responder a perguntas financeiras.
    O endpoint recebe uma pergunta e retorna uma resposta gerada pelo modelo, juntamente com as fontes utilizadas para gerar a resposta e os KPIs extraídos.
    """

    logger.info(f"[POST /query] question='{request.question[:80]}...'")
    start = time.monotonic()

    try:
        answer = run_query(
            user_query=request.question,
            session_id=request.session_id,
        )
    except Exception as e:
        logger.error(f"[POST /query] Pipeline error - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar a consulta: {str(e)}"
        )

    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipeline retornou resposta vazia",
        )
    
    elapsed_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        f"[POST /query] Concluído em {elapsed_ms}ms | "
        f"confidence={answer.confidence:.2f} | "
        f"kpis={len(answer.kpis)}"
    )

    return QueryResponse(
        answer=answer.answer,
        kpis=[
            KPIResponse(
                name=kpi.name,
                value=kpi.value,
                unit=kpi.unit,
                period=kpi.period,
                source_page=kpi.page_source,
            )
            for kpi in answer.kpis
        ],
        sources=[
            SourceResponse(
                page=s.page,
                section=s.section,
                chunk_id=s.chunk_id,
            )
            for s in answer.sources
        ],
        confidence=answer.confidence,
        need_more_context=answer.need_more_context,
        reasoning=answer.ratio,
        processing_time_ms=elapsed_ms,
    )
