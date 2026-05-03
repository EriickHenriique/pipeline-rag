from loguru import logger
from  qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchAny,
    Prefetch,
    SparseVector,
)

from fin_pipeline.agents.base import BaseAgent
from fin_pipeline.schemas.state import AgentState
from fin_pipeline.schemas.query import QueryPlan, RetrievalFilters, RetrievedChunk
from fin_pipeline.storage.embedder import EmbeddingService
from fin_pipeline.storage.qdrant_indexer import QdrantIndexer

TOP_K = 5
PREFETCH_LIMIT = 20

class RetrieverAgent(BaseAgent):
    """Agente responsável por realizar a busca vetorial no índice do Qdrant, utilizando o plano de consulta gerado pelo QueryAnalystAgent."""
    name = "retriever"

    def __init__(self):
        self._indexer = QdrantIndexer()
        self._embedder = EmbeddingService()

    def run(self, state: AgentState) -> dict:
        """Agente responsável por realizar a busca vetorial no índice do Qdrant, utilizando o plano de consulta gerado pelo QueryAnalystAgent."""

        # Recupera o plano de consulta do estado do agente
        plan: QueryPlan = state["query_plan"]
        if plan is None:
            raise RuntimeError(f"[{self.name}] falta o plano de consulta no estado do agente")
        
        # Loga a intenção e os filtros extraídos pelo QueryAnalystAgent
        logger.info(f"[{self.name}] procurando por {plan.query_reformulada}")
        
        # Realiza a busca vetorial no Qdrant, utilizando o texto reformulado para gerar os vetores de consulta e os filtros extraídos para restringir a busca
        dense_vector, sparse = self._embed_query(plan.query_reformulada)
        qdrant_filter = self._build_filter(plan.filters)

        # Loga os vetores de consulta e os filtros para debug
        results = self._indexer.client.query_points(
            collection_name=self._indexer.collection_name,
            prefetch=[Prefetch(
                query=dense_vector,
                using="dense",
                limit=PREFETCH_LIMIT,
                filter=qdrant_filter
            ),
            Prefetch(
                query=SparseVector(
                    indices=sparse["indices"],
                    values=sparse["values"]
                ),
                using="sparse",
                limit=PREFETCH_LIMIT,
                filter=qdrant_filter                
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=TOP_K,
            with_payload=True).points
        
        # Converte os resultados retornados pelo Qdrant em uma lista de RetrievedChunk, extraindo os campos relevantes do payload para cada chunk recuperado, e loga quantos chunks relevantes foram encontrados
        chunks = self._to_retrieved_chunks(results)

        logger.info(f"[{self.name}] encontrado {len(chunks)} chunks relevantes")
        return {"retrieved_chunks": chunks}

    def _embed_query(self, query_text: str) -> tuple[list[float], dict]:
        """Gera os vetores de consulta denso e esparso a partir do texto da pergunta reformulada."""
        dense = self._embedder._embed_dense_batch([query_text])[0]
        sparse_emb = self._embedder._embed_sparse_batch([query_text])[0]
        return dense, {
            "indices": sparse_emb.indices.tolist(),
            "values": sparse_emb.values.tolist(),
        }
    
    @staticmethod
    def _build_filter(filters: RetrievalFilters) -> Filter | None:
        """Constrói um filtro do Qdrant a partir dos filtros extraídos pelo QueryAnalystAgent. Retorna None se não houver filtros."""
        conditions = []
        if filters.nome_empresa:
            conditions.append(
                FieldCondition(
                    key="nome_empresa",
                    match=MatchAny(any=filters.nome_empresa)
                )
            )
        
        if filters.ano_fiscal:
            conditions.append(
                FieldCondition(
                    key="ano_fiscal",
                    match=MatchAny(any=filters.ano_fiscal)
                )
            )
        
        if filters.trimestre:
            conditions.append(
                FieldCondition(
                    key="trimestre",
                    match=MatchAny(any=filters.trimestre)
                )
            )
        
        if filters.secao:
            conditions.append(
                FieldCondition(
                    key="secao",
                    match=MatchAny(any=filters.secao)
                )
            )
        
        if not conditions:
            return None
        
        return Filter(must=conditions)
    
    @staticmethod
    def _to_retrieved_chunks(points: list) -> list[RetrievedChunk]:
        """Converte os pontos retornados pelo Qdrant em uma lista de RetrievedChunk, extraindo os campos relevantes do payload."""
        chunks = []

        # O payload deve conter: chunk_id, text, nome_empresa, ano_fiscal, trimestre, secao, page_number, chunk_type
        for point in points:
            payload = point.payload
            chunks.append(
                RetrievedChunk(
                    chunk_id=payload["chunk_id"],
                    text=payload["text"],
                    score=point.score,
                    nome_empresa=payload["nome_empresa"],
                    ano_fiscal=payload["ano_fiscal"],
                    trimestre=payload["trimestre"],
                    section=payload["secao"],
                    page_number=payload["page_number"],
                    chunk_type=payload["chunk_type"],
                )
            )
        
        return chunks


        


        


