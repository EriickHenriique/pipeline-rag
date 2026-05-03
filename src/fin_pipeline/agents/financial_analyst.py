from langchain_openai import ChatOpenAI
from loguru import logger

from fin_pipeline.agents.base import BaseAgent
from fin_pipeline.config import get_settings
from fin_pipeline.schemas.analysis import FinancialAnalysis
from fin_pipeline.schemas.query import RetrievedChunk
from fin_pipeline.schemas.state import AgentState

# Prompt para o agente de análise financeira, orientando-o a responder perguntas usando apenas os trechos fornecidos como contexto, seguindo regras específicas de citação de fontes, extração de KPIs e atribuição de níveis de confiança. O prompt é estruturado para garantir que o agente produza respostas precisas, baseadas em evidências e bem fundamentadas nos dados disponíveis. 
FINANCIAL_ANALYST_PROMPT = """"
    Você é um analista financeiro sênior especializado em DFPs brasileiras (CVM).

    Sua tarefa: responder a pergunta do usuário usando APENAS os trechos fornecidos como contexto.

    REGRAS CRÍTICAS:
    1. Use SOMENTE informações presentes nos trechos. Nunca invente dados.
    2. Se a informação não está nos trechos, diga claramente que não foi encontrada, defina need_more_context=True, sources=[] e confidence abaixo de 0.3.
    3. Sempre cite a fonte: cada fato relevante deve ter um chunk_id de origem. Se need_more_context=False, sources DEVE conter ao menos uma entrada.
    4. Para KPIs (EBITDA, Lucro Líquido, etc.), extraia: nome, valor, unidade (BRL/USD/percent), período.
    5. Atribua um confidence_score de 0.0 a 1.0:
    - 0.9-1.0: resposta direta encontrada no contexto
    - 0.6-0.8: resposta inferida do contexto
    - 0.3-0.5: contexto parcial, resposta incerta
    - 0.0-0.2: contexto insuficiente
    6. Responda em PORTUGUÊS BRASILEIRO, formal mas claro.

    PERGUNTA DO USUÁRIO:
    {query}

    KPIs ESPERADOS (se aplicável):
    {expected_kpis}

    CONTEXTO RECUPERADO:
    {context}

    Produza uma análise financeira estruturada respondendo a pergunta

    """
class FinancialAnalystAgent(BaseAgent):
    """Agente de análise financeira especializado em DFPs brasileiras, que processa os trechos recuperados e gera uma resposta estruturada com base no prompt definido."""

    name = "FinancialAnalystAgent"
    """Agente de análise financeira especializado em DFPs brasileiras, que processa os trechos recuperados"""
    def __init__(self):
        settings = get_settings()
        self.model = ChatOpenAI(
            model=settings.chat_model,
            temperature=0.2,
            api_key=settings.openai_api_key.get_secret_value()
        ).with_structured_output(FinancialAnalysis)
    
    def run(self, state: AgentState) -> dict:
        """Executa o agente de análise financeira, processando os chunks recuperados e gerando uma resposta estruturada com base no prompt definido."""
        plan = state["query_plan"]
        chunks: list[RetrievedChunk] = state["retrieved_chunks"]

        if not chunks:
            logger.warning(f"[{self.name}] não encontrou chunks para a query: {state['query']}")
            return {
                "draft_analysis": FinancialAnalysis(
                    answer="Não foi possível encontrar informações relevantes para responder à pergunta.",
                    sources=[],
                    confidence=0.0,
                    need_more_context=True
                )
            }

        logger.info(f"[{self.name}] processando {len(chunks)} chunks para a query: {plan.query_original}")

        context = self._format_context(chunks)

        prompt = FINANCIAL_ANALYST_PROMPT.format(
            query = plan.query_original,
            expected_kpis = ", ".join(plan.expected_kpis) or "Nenhum especifico",
            context = context
        )

        # Invoca o modelo para gerar a análise financeira estruturada, que inclui a resposta em linguagem natural, os KPIs extraídos, as fontes dos KPIs, o nível de confiança e uma explicação opcional do raciocínio do agente.
        analysis: FinancialAnalysis = self.model.invoke(prompt)

        logger.info(
            f"[{self.name}] Confidence={analysis.confidence:.2f} | "
            f"KPIs={len(analysis.kpis)} | Sources={len(analysis.sources)}"
        )
        return {"draft_analysis": analysis}
    
    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        """Formata os chunks recuperados em um contexto legível para o modelo, incluindo metadados como chunk_id, empresa, página, ano, trimestre e seção."""
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(
                f"[Trecho {i} | chunk_id={c.chunk_id}"
                f"| empresa={c.nome_empresa} | página={c.page_number}"
                f"| ano={c.ano_fiscal} {c.trimestre} | seção={c.section}]\n{c.text}\n"
            )

        return "\n".join(parts)
