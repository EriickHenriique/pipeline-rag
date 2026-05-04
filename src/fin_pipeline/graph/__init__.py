from langchain_core.runnables.config import RunnableConfig

from fin_pipeline.graph.builder import build_graph, get_graph
from fin_pipeline.schemas.analysis import FinancialAnalysis
from fin_pipeline.schemas.state import AgentState


def run_query(user_query: str, session_id: str | None = None) -> FinancialAnalysis | None:
    from fin_pipeline.observability.tracing import init_langfuse

    graph = get_graph()

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

    if not init_langfuse():
        final_state = graph.invoke(initial_state)
        return final_state.get("final_answer")

    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler

    langfuse = get_client()
    answer = None

    with langfuse.start_as_current_observation(
        name="fin_pipeline",
        as_type="chain",
        input={"query": user_query},
    ) as span:
        with propagate_attributes(
            trace_name="fin_pipeline-query",
            session_id=session_id,
            tags=["rag", "financial-analyst"],
        ):
            handler = CallbackHandler()
            graph_config = RunnableConfig(callbacks=[handler])
            final_state = graph.invoke(initial_state, config=graph_config)
            answer = final_state.get("final_answer")

            if answer:
                span.update(
                    output={
                        "answer": answer.answer,
                        "confidence": answer.confidence,
                        "kpi_count": len(answer.kpis),
                        "source_count": len(answer.sources),
                        "retry_count": final_state.get("retry_count", 0),
                    }
                )

    langfuse.flush()
    return answer


__all__ = ["run_query", "get_graph", "build_graph"]