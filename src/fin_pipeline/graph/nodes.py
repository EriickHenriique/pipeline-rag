from langchain_core.runnables.config import RunnableConfig

from fin_pipeline.agents.financial_analyst import FinancialAnalystAgent
from fin_pipeline.agents.query_analyst import QueryAnalystAgent
from fin_pipeline.agents.retriever import RetrieverAgent
from fin_pipeline.agents.validator import ValidatorAgent
from fin_pipeline.schemas.state import AgentState

_query_analyst_agent = QueryAnalystAgent()
_financial_analyst_agent = FinancialAnalystAgent()
_retriever_agent = RetrieverAgent()
_validator_agent = ValidatorAgent()


def node_query_analyst(state: AgentState, config: RunnableConfig) -> dict:
    return _query_analyst_agent.run(state, config=config)

def node_financial_analyst(state: AgentState, config: RunnableConfig) -> dict:
    return _financial_analyst_agent.run(state, config=config)

def node_retriever(state: AgentState, config: RunnableConfig) -> dict:
    return _retriever_agent.run(state, config=config)

def node_validator(state: AgentState) -> dict:
    return _validator_agent.run(state)