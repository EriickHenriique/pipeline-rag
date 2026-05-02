from langchain_openai import ChatOpenAI
from loguru import logger

from fin_pipeline.agents.base import BaseAgent
from fin_pipeline.config import get_settings
from fin_pipeline.schemas.query import QueryPlan
from fin_pipeline.schemas.state import AgentState


QUERY_ANALYST_PROMPT = """
        Você é um analista financeiro especializado em DFPs brasileiras.

        Sua tarefa: analisar a pergunta do usuário e produzir um plano estruturado.

        Instruções:
        1. Identifique a INTENÇÃO da pergunta:
        - kpi_lookup: usuário quer um número específico (ex: "Qual o EBITDA?")
        - comparison: comparar empresas ou períodos
        - trend_analysis: análise de evolução temporal
        - summary: resumo geral
        - explanation: explicação de causa
        - unknown: não dá pra saber
        
        2. Extraia os FILTROS:
        - Empresas mencionadas (em MAIÚSCULAS, ex: "PETROBRAS")
        - Anos fiscais (ex: 2023, 2024)
        - Trimestres (Q1, Q2, Q3, Q4, FY)
        - Seções relevantes (DRE, Balanço, DFC, DMPL, Notas Explicativas)

        3. Liste os KPIs ESPERADOS na resposta:
        - Termos como: EBITDA, Lucro Líquido, Receita Líquida, ROE, ROIC, Dívida Líquida, etc.

        4. Reformule a pergunta de forma mais clara para retrieval.

        5. Se a pergunta for muito ambígua, marque needs_clarification=true e sugira o que perguntar.

        Pergunta do usuário: {query}
"""

class QueryAnalystAgent(BaseAgent):

    name = "query_analyst"

    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.chat_model,
            temperature=0,
            api_key=settings.openai_api_key.get_secret_value(),
        ).with_structured_output(QueryPlan)
    
    def run(self, state: AgentState) -> dict:
        logger.info(f"[{self.name}] Analisando: {state['user_query']}")

        prompt = QUERY_ANALYST_PROMPT.format(query=state['user_query'])
        plan: QueryPlan = self.llm.invoke(prompt)

        plan.query_original = state['user_query']

        logger.info(
            f"[{self.name}] Intenção: {plan.intent.value} |"
            f"Filtros={plan.filters.model_dump(exclude_defaults=True)} |"
            f"KPIs={plan.expected_kpis}"
        )

        return {"query_plan": plan}
    
    
