import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from loguru import logger

from fin_pipeline.schemas.api import IngestRequest, IngestResponse
from fin_pipeline.storage.ingest_service import IngestService

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Upload e indexação de documento financeiro",
    description=(
        "Upload um arquivo PDF contendo um relatório financeiro (DFP, ITR ou Release) para ingestão no sistema. "
        "O arquivo será processado, dividido em chunks, embeddado e indexado para consultas futuras. "
    ),
)

async def ingest_document(
    # Arquivo PDF do relatório financeiro (máximo 50MB)
    file: UploadFile = File(..., description="Arquivo PDF do relatório financeiro (máximo 50MB)"),
    nome_empresa: str = Form(...),
    cnpj: str = Form(...),
    ticker: str | None = Form(default=None),
    tipo_relatorio: str = Form(...),
    ano_fiscal: int = Form(...),
    trimestre: str = Form(...),
) -> IngestResponse:
    """Endpoint para ingestão de um documento financeiro. Recebe um arquivo PDF e metadados relacionados, processa o arquivo e retorna informações sobre a ingestão."""

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas arquivos PDF são permitidos",
        )
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="O arquivo excede o tamanho máximo permitido de 50MB",
        )
    
    logger.info(f"[POST /ingest] Recebido arquivo: {file.filename} ({len(content)} bytes) - empresa={nome_empresa} ano={ano_fiscal} trimestre={trimestre}")

    with tempfile.NamedTemporaryFile(
        suffix=".pdf", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        ingest_request = IngestRequest(
            nome_empresa=nome_empresa,
            cnpj=cnpj,
            ticker=ticker,
            tipo_relatorio=tipo_relatorio,
            ano_fiscal=ano_fiscal,
            trimestre=trimestre,
        )

        service = IngestService()
        response = service.ingest(tmp_path, ingest_request)

    except ValueError as e:
        logger.error(f"[POST /ingest] Erro durante ingestão: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao processar o arquivo: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"[POST /ingest] Erro inesperado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao processar o arquivo: {str(e)}"
        )
    
    finally:
        tmp_path.unlink(missing_ok=True)

    return response

