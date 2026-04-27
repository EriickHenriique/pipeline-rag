from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuração Central. Irá ler o arquivo .env e fornecer acesso às variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI
    openai_api_key: SecretStr
    embedding_model: str = "text-embedding-3-large"
    chat_model: str = "gpt-4o-mini"
    temperature: float = 0

    # Qdrant
    qdrant_url: str
    qdrant_api_key: SecretStr
    qdrant_collection: str = "documents_chunks"

    # LangFuse
    langfuse_public_key: SecretStr
    langfuse_secret_key: SecretStr
    langfuse_host: str = "https://cloud.langfuse.com"

    # App
    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Path para o diretório raiz do projeto, útil para acessar arquivos de dados
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    @property
    def data_raw_dir(self) -> Path:
        """Path para o diretório de dados brutos."""
        return self.project_root / "data" / "raw"
    
    @property
    def data_processed_dir(self) -> Path:
        """Path para o diretório de dados processados."""
        return self.project_root / "data" / "processed"
    
    
@lru_cache()
def get_settings() -> Settings:
    """Função para obter a configuração, com cache para evitar múltiplas leituras do arquivo .env."""
    return Settings()


