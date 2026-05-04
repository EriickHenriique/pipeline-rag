from fin_pipeline.graph.builder import build_graph, get_graph
from fin_pipeline.schemas.analysis import FinancialAnalysis
from fin_pipeline.schemas.state import AgentState


def run_query(user_query: str) -> FinancialAnalysis | None:

    """Executa o pipeline financeiro para processar a consulta do usuário e retornar uma análise financeira.
    Args:
        user_query (str): A consulta do usuário a ser processada.
    Returns:
        FinancialAnalysis | None: A análise financeira resultante ou None se o processo falhar.
        
    O pipeline segue os seguintes passos:
    1. O nó "query_analyst" analisa a consulta do usuário e
    gera um plano de consulta.
    2. O nó "retriever" recupera os dados relevantes com base no plano
    de consulta.
    3. O nó "financial_analyst" processa os dados recuperados e gera uma análise financeira preliminar.
    4. O nó "validator" valida a análise financeira preliminar. Se a validação falhar, o processo pode ser reiniciado a partir do nó
    "financial_analyst" para tentar gerar uma análise diferente. Se a validação for bem-sucedida, o processo é concluído e a análise final é retornada.

    """
    graph = get_graph()

    # Define o estado inicial do agente com a consulta do usuário e valores padrão para os outros campos
    initial_state: AgentState = {
        "user_query": user_query,
        "query_plan": None,
        "retrieved_chunks": [],
        "draft_analysis": None,
        "validation_result": None,
        "is_valid": False,
        "validation_errors": [],
        "retry_count": 0,
        "next_agent": "",
        "is_done": False,
        "final_answer": None,
    }

    final_state = graph.invoke(initial_state)
    return final_state.get("final_answer")


__all__ = ["run_query", "get_graph", "build_graph"]