from typing import Literal

from pydantic import BaseModel, Field, field_validator

class KPI(BaseModel):
    """Modelo de dados para um KPI extraído de um chunk de texto, contendo o nome do KPI, seu valor numérico, unidade de medida, período fiscal a que se refere, e a página do relatório de onde foi extraído, se disponível."""
    name: str = Field(description="EBITDA, Lucro Líquido, ROE, Receita Líquida, etc.")
    value: float = Field(description="Valor numérico do KPI, já convertido para um formato numérico, ex: 1.5M -> 1500000.0")
    unit: Literal["BRL", "USD", "percent", "ratio", "units"] = Field(description="Unidade do KPI, ex: BRL para valores monetários, % para margens, units para contagens")
    period: str = Field(description="Período fiscal a que o KPI se refere, ex: '2023-Q4', '2023', '2023-Q1', etc.")
    page_source: int | None = Field(description="Número da página do relatório de onde o KPI foi extraído, se disponível")

    @field_validator("nome")
    @classmethod
    def normalize_nome(cls, v: str) -> str:
        return v.strip().title()
    
class Source(BaseModel):
    """Modelo de dados para a fonte de um KPI, contendo o identificador do chunk de onde o KPI foi extraído, a página do relatório, e a seção do relatório."""
    chunk_id: str = Field(description="Identificador do chunk de onde o KPI foi extraído")
    page: int = Field(description="Número da página do relatório de onde o KPI foi extraído")
    section: str = Field(description="Seção do relatório de onde o KPI foi extraído, ex: 'Demonstração de Resultados', 'Balanço Patrimonial', etc.")    

class FinancialAnalysis(BaseModel):
    """Modelo de dados para a resposta de análise financeira gerada pelo agente, contendo a resposta em linguagem natural, a lista de KPIs extraídos dos chunks relevantes, as fontes desses KPIs, e uma explicação opcional do raciocínio do agente."""
    answer: str = Field(min_length=10, description="Resposta gerada pelo agente em linguagem natural Português do Brasil, contendo a análise financeira solicitada pelo usuário, baseada nos KPIs extraídos dos chunks relevantes.")
    kpis: list[KPI] = Field(default_factory=list, description="Lista de KPIs extraídos dos chunks relevantes e incluídos na resposta, com seus valores numéricos, unidades, períodos e páginas de origem.")
    sources: list[Source] = Field(default_factory=list, description="Lista de fontes dos KPIs incluídos na resposta, contendo os identificadores dos chunks de onde os KPIs foram extra ídos, as páginas dos relatórios e as seções dos relatórios de onde os chunks foram extraídos.")
    confidence: float = Field(ge=0.0, le=1.0, description="Nível de confiança do agente na resposta gerada, baseado na relevância dos chunks recuperados e na consistência dos KPIs extraídos, expresso como um valor entre 0.0 (sem confiança) e 1.0 (confiança total).")
    need_more_context: bool = False
    ratio: str | None = Field(default=None, description="Explicação Opcional em como o agente chegou aquela resposta baseada nos KPIs extraídos, útil para análise e debugging do processo de raciocínio do agente.")
