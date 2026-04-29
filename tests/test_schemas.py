import pytest 
from pydantic import ValidationError


from fin_pipeline.schemas import (
    DFPMetadata,
    FinancialAnalysis,
    KPI,
    QueryIntent,
    QueryPlan,
    ReportType,
    RetrievalFilters,
    Source,
)

# Document Schemas


class TestDFPMetadata:    
    """Testes para o modelo DFPMetadata, verificando a validação e normalização dos campos, como o formato do CNPJ, os limites para o ano fiscal, e a normalização do nome da empresa e ticker para maiúsculas."""
    # Testa a criação de um objeto DFPMetadata válido, verificando a normalização do nome da empresa e do ticker para maiúsculas.
    def test_valid(self):
        meta = DFPMetadata(
            nome_empresa="Petrobras",
            cnpj="33.000.167/0001-01",
            ticker="petr4",
            tipo_relatorio=ReportType.DFP,
            ano_fiscal=2024,
            trimestre=4,
            data_publicacao="2024-02-15"
        )
        assert meta.nome_empresa == "PETROBRAS"
        assert meta.ticker == "PETR4"

    # Testa a validação do formato do CNPJ, esperando um erro de validação para um CNPJ inválido.
    def test_invalid_cnpj(self):
        with pytest.raises(ValidationError):
            DFPMetadata(
                nome_empresa="Petrobras",
                cnpj="invalido",
                ticker="petr4",
                tipo_relatorio=ReportType.DFP,
                ano_fiscal=2024,
                trimestre=4,
                data_publicacao="2024-02-15"
            )
    # Testa a validação do ano fiscal, esperando um erro de validação para um ano fora dos limites definidos (2010-2030).
    def test_invalid_year(self):
        with pytest.raises(ValidationError):
            DFPMetadata(
                nome_empresa="Petrobras",
                cnpj="33.000.167/0001-01",
                ticker="petr4",
                tipo_relatorio=ReportType.DFP,
                ano_fiscal=1990,
                trimestre=3,
                data_publicacao="2024-02-15"
            )

# Query Schemas
class TestQueryPlan:
    """Testes para o modelo QueryPlan, verificando a criação de um plano de consulta válido, a identificação da intenção de consulta, a aplicação dos filtros de recuperação, e a necessidade de esclarecimentos adicionais quando a intenção é desconhecida."""
   
    # Testa a criação de um plano de consulta válido, verificando a identificação da intenção de consulta e a aplicação dos filtros de recuperação.
    def test_valid(self):
        plan = QueryPlan(
            query_original="Qual o EBITDA da Petrobras em 2024?",
            intent=QueryIntent.KPI_LOOKUP,
            query_reformulada="EBITDA Petrobras 2024",
            filters=RetrievalFilters(
                nome_empresa=["PETROBRAS"],
                anos_fiscais=[2024],
            ),
            expected_kpis=["EBITDA"],
                    )
        assert plan.intent == QueryIntent.KPI_LOOKUP
        assert "PETROBRAS" in plan.filters.nome_empresa
    # Testa a necessidade de esclarecimentos adicionais quando a intenção de consulta é desconhecida, verificando se a mensagem de esclarecimento é fornecida corretamente.
    def test_clarification(self):
        plan = QueryPlan(
            query_original="show me the numbers",
            intent=QueryIntent.UNKNOWN,
            query_reformulada="show me the numbers",
            filters=RetrievalFilters(),
            needs_clarification=True,
            clarification_message="Qual empresa e período?",
        )
        assert plan.needs_clarification is True
    
# Analysis Schemas
class TestFinancialAnalysis:
    """Testes para o modelo FinancialAnalysis, verificando a criação de uma análise financeira válida, a normalização do nome dos KPIs, a necessidade de pelo menos uma fonte para os KPIs incluídos na resposta, e os limites para o nível de confiança do agente."""
    # Testa a criação de uma análise financeira válida, verificando a normalização do nome dos KPIs para título (title case).
    def test_valid(self):
        analysis = FinancialAnalysis(
            answer="O EBITDA da Petrobras em 2024 foi R$ 78 bilhões.",
            kpis=[
                KPI(name="ebitda", value=78_000_000_000, unit="BRL", period="2024-FY"),
            ],
            sources=[Source(chunk_id="abc-123", page=47, section="DRE")],
            confidence=0.95,
        )
        assert analysis.kpis[0].name == "Ebitda" 

    # Testa a validação para garantir que pelo menos uma fonte seja fornecida quando KPIs são incluídos na resposta, esperando um erro de validação se a lista de fontes estiver vazia.
    def test_requires_at_least_one_source(self):
        with pytest.raises(ValidationError):
            FinancialAnalysis(
                answer="Some answer here.",
                sources=[], 
                confidence=0.5,
            )
    # Testa os limites para o nível de confiança do agente, esperando um erro de validação se o valor de confiança estiver fora do intervalo permitido (0.0 a 1.0).
    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            FinancialAnalysis(
                answer="Some answer here.",
                sources=[Source(chunk_id="x", page=1, section="DRE")],
                confidence=1.5,
            )

