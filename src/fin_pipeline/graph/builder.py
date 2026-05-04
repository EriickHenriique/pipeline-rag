from langgraph.graph import END, START, StateGraph

from fin_pipeline.graph.edges import route_after_validation
from fin_pipeline.graph.nodes import (
    node_financial_analyst,
    node_query_analyst,
    node_retriever,
    node_validator
    )

from fin_pipeline.schemas.state import AgentState


def build_graph():
    """Constrói o grafo de estados para o pipeline financeiro."""

    # Cria o grafo de estados
    graph = StateGraph(AgentState)

    # Registra os nós no grafo
    graph.add_node("query_analyst", node_query_analyst)
    graph.add_node("retriever", node_retriever)
    graph.add_node("financial_analyst", node_financial_analyst)
    graph.add_node("validator", node_validator)

    # Registra as arestas no grafo
    graph.add_edge(START, "query_analyst")
    graph.add_edge("query_analyst", "retriever")
    graph.add_edge("retriever", "financial_analyst")
    graph.add_edge("financial_analyst", "validator")

    # Registra as arestas condicionais para o nó de validação
    graph.add_conditional_edges(
        source="validator",
        path=route_after_validation,
        path_map={
            "retry": "financial_analyst",
            "end": END
        }
    )

    # Compila o grafo para otimização
    return graph.compile()

_graph = None

def get_graph():
    """Retorna o grafo de estados, construindo-o se ainda não tiver sido criado."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

