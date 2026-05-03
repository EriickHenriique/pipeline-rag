from operator import add
from typing import Annotated, TypedDict

from fin_pipeline.schemas.analysis import FinancialAnalysis
from fin_pipeline.schemas.query import QueryPlan, RetrievedChunk
from fin_pipeline.schemas.validation import ValidationResult

class AgentState(TypedDict):
    """"Modelo de estado compartilhado entre os agentes, que inclui a consulta do usuário, o plano de consulta gerado pelo agente
    de planejamento, os trechos recuperados pelo agente de recuperação, a análise financeira gerada pelo agente de análise, 
    o resultado da validação realizada pelo agente de validação, indicadores de controle de fluxo para gerenciamento de
    tentativas e definição do próximo agente a ser executado, e o resultado final da resposta que será apresentada ao usuário. """

   # Entrada do usuário
    user_query: str

    # Planejamento de consulta
    query_plan: QueryPlan | None

    # Recuperação de trechos
    retrieved_chunks: list[RetrievedChunk]

    # Análise financeira
    draft_analysis: FinancialAnalysis | None

    # Validação
    validation_result: ValidationResult | None
    is_valid: bool
    validation_errors: Annotated[list[str], add]

    # Controle de fluxo
    retry_count: int
    next_agent: str
    is_done: bool

    # Saída final
    final_answer: FinancialAnalysis | None