from operator import add
from typing import Annotated, TypedDict

from fin_pipeline.schemas.analysis import FinancialAnalysis
from fin_pipeline.schemas.query import QueryPlan, RetrievedChunk

class AgentState(TypedDict):
    """Estado do agente durante o processo de análise financeira, contendo a pergunta original do usuário, 
    o plano de consulta gerado, os chunks recuperados, a análise financeira rascunho gerada, a validade da resposta, 
    erros de validação, contagem de tentativas, próximo agente a ser acionado, status de conclusão, 
    e a resposta final após validação e possíveis iterações adicionais."""

    user_query: str

    query_plan: QueryPlan

    retrieved_chunks: list[RetrievedChunk]

    draft_analysis: FinancialAnalysis

    is_valid: bool
    validation_errors: Annotated[list[str], add]

    retry_count: int
    next_agent: str
    is_done: bool

    final_answer: FinancialAnalysis