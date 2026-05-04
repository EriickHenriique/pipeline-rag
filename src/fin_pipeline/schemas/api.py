from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# Requests

class QueryRequest(BaseModel):
    """Modelo de dados para a requisição de consulta ao modelo de linguagem."""
    question: str = Field(
        min_length=5,
        max_length=1000,
        description="Pergunta do usuário para o modelo de linguagem. (Português ou Inglês)",
        examples=["Qual foi o lucro líquido da empresa no último ano?"]
    )
    session_id: str | None = Field(
        default=None,
        description="Identificador único para a sessão do usuário. (opcional, mas recomendado para manter o contexto entre perguntas)"
    )

# Responses

class KPIResponse(BaseModel):
    """Modelo de dados para representar um KPI extraído do relatório financeiro."""
    name: str
    value: float
    unit: str
    period: str
    source_page: int | None = None

class SourceResponse(BaseModel):
    """Modelo de dados para representar uma fonte de informação (chunk) utilizada na resposta do modelo de linguagem."""
    page: int
    section: str
    chunk_id: str

class QueryResponse(BaseModel):
    """Modelo de dados para a resposta do modelo de linguagem à consulta do usuário."""
    answer: str
    kpis: list[KPIResponse]
    sources: list[SourceResponse]
    confidence: float
    need_more_context: bool
    reasoning: str | None = None
    processing_time_ms: int

class DocumentInfo(BaseModel):
    """Modelo de dados para representar informações sobre um documento financeiro processado."""
    nome_empresa: str
    ano_fiscal: int
    trimestre: int
    tipo_relatorio: str
    chunk_count: int

class HealthResponse(BaseModel):
    """Modelo de dados para a resposta da rota de saúde do serviço."""
    status: Literal["ok", "degraded", "error"]
    qdrant_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "0.1.0"

class ErrorResponse(BaseModel):
    """Modelo de dados para a resposta de erro do serviço."""
    error: str
    detail: str | None = None
    status_code: int

class IngestRequest(BaseModel):
    """Modelo de dados para a requisição de ingestão de um documento financeiro."""
    nome_empresa: str = Field(min_length=2, max_length=200)
    cnpj: str = Field(
        pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$",
        examples=["33.000.167/0001-01"],
    )
    ticker: str | None = Field(default=None, max_length=10)
    tipo_relatorio: str = Field(
        description="DFP, ITR or Release",
        examples=["DFP"],
    )
    ano_fiscal: int = Field(ge=2010, le=2030)
    trimestre: int = Field(
        description="1, 2, 3, 4",
        examples=[4],
    )

class IngestResponse(BaseModel):
    """Modelo de dados para a resposta da ingestão de um documento financeiro."""

    nome_empresa: str
    ano_fiscal: int
    trimestre: int
    total_chunks: int
    table_chunks: int
    text_chunks: int
    processing_time_ms: int
    collection_name: str
    success: bool
    message: str
