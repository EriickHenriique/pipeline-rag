from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from fin_pipeline.api.routes import documents, health, query
from fin_pipeline.config import get_settings
from fin_pipeline.graph import get_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de contexto para o ciclo de vida da aplicação FastAPI."""
    logger.info("Iniciando o serviço de API...")

    get_graph()

    logger.info("Serviço de API iniciado com sucesso.")

    yield 

    logger.info("Encerrando o serviço de API...")

def create_app() -> FastAPI:
    """Função para criar e configurar a aplicação FastAPI."""
    settings = get_settings()

    # Configurações adicionais podem ser feitas aqui, como conexão com bancos de dados, inicialização de clientes, etc.
    app = FastAPI(
        title="Pipeline Financeiro - API",
        description="API para consulta de relatórios financeiros usando modelos de linguagem.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Configuração de CORS para permitir requisições do frontend (Streamlit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8501",
            "http://127.0.0.1:8501"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inclusão das rotas da API
    app.include_router(health.router, tags=["Health"])
    app.include_router(query.router, tags=["Query"])
    app.include_router(documents.router, tags=["Documents"])


    return app

app = create_app()