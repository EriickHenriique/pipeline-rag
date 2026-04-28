from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

class QueryIntent(str, Enum):
    """Intenções de consulta que o agente pode identificar a partir da pergunta do usuário."""
    KPI_LOOKUP = "kpi_lookup" # Consulta direta de um KPI específico
    COMPARISON = "comparison" # Comparação entre KPIs ou períodos
    TREND_ANALYSIS = "trend_analysis" # Análise de tendências ao longo do tempo
    SUMMARY = "summary" # Resumo geral do desempenho financeiro
    EXPLANATION = "explanation" # Explicação de um resultado ou variação
    UKNOWN = "unknown" # Intenção desconhecida ou não classificada

class RetrievalFilters(BaseModel):
    """Filtros opcionais para refinar a busca por chunks relevantes no Qdrant, com base nos metadados dos documentos."""
    nome_empresa: list[str] = Field(default_factory=list, description="Lista de nomes de empresas para filtrar os chunks")
    anos_fiscais: list[int] = Field(default_factory=list, description="Lista de anos fiscais para filtrar os chunks")
    trimestres: list[Literal[1, 2, 3, 4]] = Field(default_factory=list, description="Lista de trimestres para filtrar os chunks")
    secoes: list[str] = Field(default_factory=list, description="Lista de seções do relatório para filtrar os chunks, ex: 'Demonstração de Resultados', 'Balanço Patrimonial'")

class QueryPlan(BaseModel):
    """Plano de consulta gerado a partir da pergunta do usuário, contendo a intenção identificada, a pergunta reformulada para otimizar a recuperação de chunks relevantes, e os filtros de recuperação baseados nos metadados dos documentos."""
    query_original: str = Field(description="Pergunta original do usuário")
    intencao: QueryIntent = Field(description="Intenção de consulta identificada a partir da pergunta do usuário")
    query_reformulada: str = Field(description="Pergunta reformulada para otimizar a recuperação de chunks relevantes")
    filtros: RetrievalFilters = Field(description="Filtros de recuperação para refinar a busca por chunks relevantes no Qdrant")
    indicadores_esperados: list[str] = Field(default_factory=list, description="Lista de KPIs esperados na resposta, se aplicável")
    needs_clarification: bool = False
    clarrification_message: str | None = None  

class RetrievedChunk(BaseModel):
    """Modelo de dados para um chunk recuperado do Qdrant, contendo o texto do chunk e os metadados associados."""
    chunk_id: str = Field(description="Identificador único do chunk")
    texto: str = Field(description="Texto do chunk recuperado")
    score: float = Field(ge=0.0, le=1.0, description="Pontuação de relevância do chunk em relação à consulta")
    nome_empresa: str = Field(description="Nome da empresa associada ao chunk")
    ano_fiscal: int = Field(description="Ano fiscal associado ao chunk")
    trimestre: Literal[1, 2, 3, 4] | None = Field(description="Trimestre associado ao chunk")
    secao: str = Field(description="Seção do relatório associada ao chunk, ex: 'Demonstração de Resultados', 'Balanço Patrimonial'")
    numero_pagina: int = Field(description="Número da página de onde o chunk foi extraído")
    chunk_type: Literal["text", "table", "title"] = Field(description="Tipo do chunk: texto, tabela ou título")