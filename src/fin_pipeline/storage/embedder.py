from typing import TYPE_CHECKING

from loguru import logger
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# Importações de configuração e schemas
from fin_pipeline.config import get_settings
from fin_pipeline.schemas.document import Chunk
from fin_pipeline.schemas.storage import EmbeddedChunk



# Este código implementa um embedder para chunks de documentos, utilizando OpenAI e fastembed.
if TYPE_CHECKING:
    from fastembed import SparseEmbedding, SparseTextEmbedding

# Configurações e constantes
DENSE_VECTOR_SIZE = 3072

EMBED_BATCH_SIZE = 64


class EmbeddingService():
    """Serviço responsável por gerar embeddings densos e esparsos para chunks de documentos, utilizando OpenAI e fastembed."""
    def __init__(self):
        settings = get_settings()
        self.openai = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.embedding_model = settings.embedding_model
        self.sparse_model = SparseTextEmbedding | None = None

    # Método para gerar embedding denso usando OpenAI
    @property
    def sparse_model(self) -> SparseTextEmbedding:
        """Propriedade para acessar o modelo de embedding esparso, com lazy loading."""
        if self.sparse_model is None:
            from fastembed import SparseTextEmbedding
            logger.info("Carregando modelo de embedding esparso...")
            self.sparse_model = SparseTextEmbedding(model="Qdrant/bm25")
            logger.info("Modelo de embedding esparso carregado.")
        return self.sparse_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )

    def embed_dense_batch(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings densos para uma lista de textos, utilizando OpenAI."""
        response = self.openai.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [embedding.embedding for embedding in response.data]

    def embed_sparse_batch(self, texts: list[str]) -> list[SparseEmbedding]:
        """Gera embeddings esparsos para uma lista de textos, utilizando o modelo de embedding esparso."""
        return list(self.sparse_model.embed(texts))
    
    def embed_chunks(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """Gera embeddings densos e esparsos para uma lista de chunks, utilizando OpenAI e o modelo de embedding esparso."""

        if not chunks:
            return []
        
        logger.info(f"Gerando embeddings para {len(chunks)} chunks...")

        # Gerar embeddings em batches para evitar sobrecarregar a API e otimizar o processo
        embedded: list[EmbeddedChunk] = []

        # Processar os chunks em batches para otimizar o uso da API e evitar timeouts
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i : i + EMBED_BATCH_SIZE]
            texts = [c.text for c in batch]

            dense_vectors = self.embed_dense_batch(texts)

            sparse_embeddings = self.embed_sparse_batch(texts)

            # Combinar os resultados densos e esparsos para criar os EmbeddedChunk
            for chunk, dense, sparse in zip(batch, dense_vectors, sparse_embeddings):
                embedded.append(
                    EmbeddedChunk(
                        chunk=chunk,
                        dense_vector=dense,
                        sparse_indices=sparse.indices.tolist(),
                        sparse_values=sparse.values.tolist(),
                    )
                )

            logger.info(f"Embeddings gerados para {min(i + EMBED_BATCH_SIZE, len(chunks))} de {len(chunks)} chunks.")

        logger.info("Embeddings gerados para todos os chunks.")
        return embedded



    

    










