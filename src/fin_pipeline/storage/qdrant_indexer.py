import time
from uuid import uuid4

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams
)

from fin_pipeline.config import get_settings
from fin_pipeline.schemas.document import Chunk
from fin_pipeline.schemas.storage import EmbeddedChunk, IndexingStats

# Configurações e constantes
UPLOAD_BATCH_SIZE = 64


class QdrantIndexer():
    """Classe responsável por gerenciar a indexação de chunks no Qdrant, incluindo criação de coleção, upload de dados e obtenção de estatísticas."""
    def __init__(self):
        """Inicializa o cliente do Qdrant e define a coleção a ser usada."""
        settings = get_settings()
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key.get_secret_value(),
            timeout=60
        )
        self.collection = settings.qdrant_collection

    @property
    def client(self) -> QdrantClient:
        return self._client
    
    def collection_exists(self) -> bool:
        """Verifica se a coleção existe no Qdrant."""
        return self.client.collection_exists(collection_name=self.collection)
    
    def create_collection(self, recreate: bool = False) -> None:
        """Cria a coleção no Qdrant, com configuração para busca híbrida. Se 'recreate' for True, a coleção será recriada mesmo que já exista."""

        if recreate and self.collection_exists():
            logger.warning(f"Coleção '{self.collection}' já existe. Recriando...")
            self.client.delete_collection(collection_name=self.collection)
        
        if self.collection_exists():
            logger.info(f"Coleção '{self.collection}' já existe. Nenhuma ação necessária.")
            return

        logger.info(f"Criando coleção '{self.collection}'...")

        # Configuração da coleção para suportar busca híbrida, com vetores densos e esparsos, e índices de payload para os campos relevantes dos chunks.
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": VectorParams(
                    size=3072,
                    distance=Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False),
                ),
            },
        )

        # Criar índices de payload para os campos relevantes
        self.create_payload_indexes()

        logger.info(f"Coleção '{self.collection}' pronta para busca híbrida.")

    def create_payload_indexes(self) -> None:
        """Cria índices de payload para os campos definidos em Chunk.payload_indexes()."""
        index_specs = Chunk.payload_indexes()

        # O Qdrant suporta tipos de índice específicos, então mapeei os tipos de campo para os tipos de índice do Qdrant
        type_map = {
            "keyword": PayloadSchemaType.KEYWORD,
            "integer": PayloadSchemaType.INTEGER,
        }

        # Criar índices de payload para cada campo especificado, usando o tipo de índice apropriado
        for field_name, schema_type in index_specs.items():
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name=field_name,
                field_schema=type_map[schema_type],
            )
            logger.info(f"Índice de payload criado para campo '{field_name}' com tipo '{schema_type}'.")
    
    def upload(self, embedded_chunks: list[EmbeddedChunk]) -> IndexingStats:
        """Faz upload dos EmbeddedChunks para o Qdrant em lotes, e retorna estatísticas de indexação."""
        if not embedded_chunks:
            return IndexingStats(
                total_chunks=0, successful=0, failed=0,
                collection_name=self.collection, duration_seconds=0.0
            )
    
        if not self.collection_exists():
            raise RuntimeError(
                f'Coleção "{self.collection}" não existe. Por favor, crie a coleção antes de fazer upload dos chunks.'
                f' Use o método create_collection() para criar a coleção.'
            )
        
        # Registrar o início do processo de upload para monitoramento de desempenho
        start = time.time()
        successful = 0
        failed = 0

        # Processar os EmbeddedChunks em lotes para otimizar o upload e evitar sobrecarga do servidor
        for i in range(0, len(embedded_chunks), UPLOAD_BATCH_SIZE):
            batch = embedded_chunks[i:i + UPLOAD_BATCH_SIZE]
            points = self.build_points(batch)

            try:
                self.client.upsert(
                    collection_name=self.collection,
                    points=points,
                )
                successful += len(points)
                logger.info(f"Batch {i // UPLOAD_BATCH_SIZE + 1}: {len(points)} chunks indexados com sucesso.")
            except Exception as e:
                failed += len(points)
                logger.error(f"Batch {i // UPLOAD_BATCH_SIZE + 1}: Falha ao indexar {len(points)} chunks. Erro: {e}")
            
        duration = time.time() - start
        logger.info(f"Indexação concluída: {successful} chunks indexados com sucesso, {failed} chunks falharam. Duração: {duration:.2f} segundos.")

        # Gerar estatísticas de indexação
        stats = IndexingStats(
            total_chunks=len(embedded_chunks),
            successful=successful,
            failed=failed,
            collection_name=self.collection,
            duration_seconds=duration
        )

        logger.info(f'Upload completo - Total: {stats.total_chunks}, Sucesso: {stats.successful}, Falha: {stats.failed}, Taxa de Sucesso: {stats.success_rate:.2%}, Duração: {stats.duration_seconds:.2f} segundos.')
        return stats
    
    @staticmethod
    def build_points(embedded_chunks: list[EmbeddedChunk]) -> list[PointStruct]:
        """Constrói uma lista de PointStructs a partir de uma lista de EmbeddedChunks, formatando os dados para o formato esperado pelo Qdrant."""
        points = []
        for ec in embedded_chunks:
            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector={
                        "dense": ec.dense_vector,
                        "sparse": SparseVector(
                            indices=ec.sparse_indices,
                            values=ec.sparse_values
                        ),
                    },
                    payload={
                        "chunk_id": ec.chunk.chunk_id,
                        **ec.chunk.qdrant_payload(),
                    },
                )
            )
        return points
    
    def get_stats(self) -> dict:
        """Obtém estatísticas da coleção, como número de vetores e status."""

        # Obter informações da coleção para calcular estatísticas relevantes, como número total de vetores, vetores indexados e status da coleção.
        info = self.client.get_collection(collection_name=self.collection)
        return {
            "name": self.collection,
            "vectors_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": info.status,
        }