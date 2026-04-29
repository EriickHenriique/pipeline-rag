from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class ReportType(str, Enum):
    """Tipos de relatório que o agente pode gerar."""
    DFP = "DFP" # Demonstração Financeira Padronizada
    ITR = "ITR" # Informações Trimestrais
    RELEASE = "Release" # Comunicados de Resultados

class DocumentSection(str, Enum):
    """Seções específicas de um relatório financeiro."""
    DRE = "DRE" # Demonstração do Resultado do Exercício
    BALANCO = "Balanço" # Balanço Patrimonial
    DFC = "DFC" # Demonstração do Fluxo de Caixa
    DMPL = "DMPL" # Demonstração das Mutações do Patrimônio Líquido
    NOTAS = "Notas Explicativas" # Notas Explicativas
    RELATORIO = "Relatório" # Relatório Completo
    OUTROS = "Outros" # Outras seções ou documentos relacionados

class DFPMetadata(BaseModel):
    """Metadados Extraidos de um Relatório Financeiro na Ingestão."""
    nome_empresa: str = Field(min_length=2, max_length=200, description="Nome da empresa")
    cnpj: str = Field(pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", description="CNPJ da empresa")
    ticker: str | None = Field(default=None, min_length=1, max_length=10, description="Ticker da empresa")
    tipo_relatorio: ReportType = Field(description="Tipo de relatório financeiro")
    ano_fiscal: int = Field(ge=2010, le=2030, description="Ano fiscal do relatório")
    trimestre: Literal[1, 2, 3, 4] | None = Field(default=None, description="Trimestre do relatório")
    data_publicacao: datetime | None = Field(description="Data de publicação do relatório")

    # Validadores para normalização e validação dos campos

    # O nome da empresa é normalizado para maiúsculas e sem espaços extras
    @field_validator("nome_empresa")
    @classmethod
    def normalize_nome_empresa(cls, v: str) -> str:
        return v.strip().upper()
    
    # O ticker é normalizado para maiúsculas e sem espaços extras, se fornecido
    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None
    
class Chunk(BaseModel):
    """Modelo de dados para um chunk de texto extraído de um relatório financeiro."""
    chunk_id: str = Field(description="Identificador único do chunk")
    text: str = Field(min_length=10, description="Texto do chunk, mínimo 10 caracteres")
    page_number: int = Field(ge=1, description="Número da página de onde o chunk foi extraído")
    section: DocumentSection = Field(description="Seção do relatório a que o chunk pertence")
    chunk_type: Literal["text", "table", "title"] = Field(description="Tipo do chunk: texto, tabela ou título")
    char_count: int = Field(ge=10, description="Número de caracteres no chunk, mínimo 10")
    document_metadata: DFPMetadata = Field(description="Metadados do documento de onde o chunk foi extraído")

    def qdrant_payload(self) -> dict:
        """Gera o payload a ser enviado para o Qdrant, combinando o texto do chunk com os metadados do documento."""
        return {
            "text": self.text,
            "page_number": self.page_number,
            "section": self.section.value,
            "chunk_type": self.chunk_type,
            "nome_empresa": self.document_metadata.nome_empresa,
            "cnpj": self.document_metadata.cnpj,
            "ticker": self.document_metadata.ticker,
            "tipo_relatorio": self.document_metadata.tipo_relatorio.value,
            "ano_fiscal": self.document_metadata.ano_fiscal,
            "trimestre": self.document_metadata.trimestre,
            "ano_publicacao": self.document_metadata.data_publicacao.isoformat() if self.document_metadata.data_publicacao else None
        }

    @classmethod
    def payload_indexes(cls) -> list[str]:
        """Retorna a lista de chaves do payload que devem ser indexadas no Qdrant."""
        return [
            "text",
            "page_number",
            "section",
            "chunk_type",
            "nome_empresa",
            "cnpj",
            "ticker",
            "tipo_relatorio",
            "ano_fiscal",
            "trimestre",
            "ano_publicacao"
        ]  
