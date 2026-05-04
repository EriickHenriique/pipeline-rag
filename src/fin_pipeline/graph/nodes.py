from fin_pipeline.agents.financial_analyst import FinancialAnalystAgent
from fin_pipeline.agents.query_analyst import QueryAnalystAgent
from fin_pipeline.agents.retriever import RetrieverAgent
from fin_pipeline.agents.validator import ValidatorAgent
from fin_pipeline.schemas.state import AgentState

# Instância dos agentes, que serão usados pelos nós do pipeline. Cada agente é responsável por uma tarefa específica, como analisar consultas, realizar análises financeiras, recuperar informações ou validar resultados. Esses agentes são criados uma vez e reutilizados em cada nó do pipeline para garantir consistência e eficiência.
_query_analyst_agent = QueryAnalystAgent()
_financial_analyst_agent = FinancialAnalystAgent()
_retriever_agent = RetrieverAgent()
_validator_agent = ValidatorAgent()


# Nodes do pipeline, cada um executa um agente específico e retorna o resultado para o próximo nó. O estado do agente é passado como argumento para cada nó, permitindo que os agentes acessem e modifiquem o estado conforme necessário. O resultado de cada nó é um dicionário que pode conter informações relevantes para o próximo nó no pipeline.
def node_query_analyst(state: AgentState) -> dict:
    return _query_analyst_agent.run(state)

def node_financial_analyst(state: AgentState) -> dict:
    return _financial_analyst_agent.run(state)

def node_retriever(state: AgentState) -> dict:
    return _retriever_agent.run(state)

def node_validator(state: AgentState) -> dict:
    return _validator_agent.run(state)