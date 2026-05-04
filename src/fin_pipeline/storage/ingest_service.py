import time
from pathlib import Path

from loguru import logger

from fin_pipeline.ingestion.chunker import DFPChunker
from fin_pipeline.ingestion.parser import DFPParser
from fin_pipeline.schemas.api import IngestRequest, IngestResponse
from fin_pipeline.schemas.document import DFPMetadata, ReportType
from fin_pipeline.storage.embedder import EmbeddingService
from fin_pipeline.storage.qdrant_indexer import QdrantIndexer


class IngestService:
    """Serviço responsável por orquestrar o processo de ingestão de documentos financeiros."""
    def __init__(self):
        self._parser = DFPParser(do_table_structure=True)
        self._chunker = DFPChunker()
        self._embedder = EmbeddingService()
        self._indexer = QdrantIndexer()

    def ingest(self, pdf_path: Path, request: IngestRequest) -> IngestResponse:
        """Processa a ingestão de um documento financeiro, desde o parsing até a indexação."""

        start = time.monotonic()
        logger.info(
            f"[IngestService] Iniciando ingestão: "
            f"{request.nome_empresa} {request.ano_fiscal} {request.trimestre}"
        )

        # Passo 1: Validação metadata (Pydantic DFPMetadata)
        metadata = DFPMetadata(
            nome_empresa=request.nome_empresa,
            cnpj=request.cnpj,
            ticker=request.ticker,
            tipo_relatorio=ReportType(request.tipo_relatorio),
            ano_fiscal=request.ano_fiscal,
            trimestre=request.trimestre,
        )
        logger.info(f"[IngestService] Metadata validated: {metadata.nome_empresa}")

        # Passo 2: Parse PDF with Docling
        parsed = self._parser.parse(pdf_path)
        logger.info(
            f"[IngestService] Parsed: {parsed['page_count']} páginas, "
            f"{len(parsed['tables'])} tabelas, {len(parsed['pages'])} páginas com conteúdo"
        )

        # Passo 3: Chunk 
        chunks = self._chunker.chunk(parsed, metadata)
        table_chunks = sum(1 for c in chunks if c.chunk_type == "table")
        text_chunks = sum(1 for c in chunks if c.chunk_type == "text")
        logger.info(
            f"[IngestService] Chunked: {len(chunks)} total "
            f"({table_chunks} tabelas, {text_chunks} blocos de texto)"
        )

        # Passo 4: Criar coleção no Qdrant (se não existir) 
        if not self._indexer.collection_exists():
            self._indexer.create_collection()

        # Passo 5: Embedding
        embedded = self._embedder.embed_chunks(chunks)
        logger.info(f"[IngestService] Embedded: {len(embedded)} chunks")

        # Passo 6: Upload no Qdrant
        stats = self._indexer.upload(embedded)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            f"[IngestService] Concluído em {elapsed_ms}ms | "
            f"success={stats.successful}/{stats.total_chunks}"
        )

        return IngestResponse(
            nome_empresa=metadata.nome_empresa,
            ano_fiscal=metadata.ano_fiscal,
            trimestre=metadata.trimestre,
            total_chunks=stats.total_chunks,
            table_chunks=table_chunks,
            text_chunks=text_chunks,
            processing_time_ms=elapsed_ms,
            collection_name=stats.collection_name,
            success=stats.failed == 0,
            message=(
                f"Indexação concluída com sucesso: {stats.successful} chunks"
                if stats.failed == 0
                else f"Indexação concluída com erros: {stats.successful} chunks, {stats.failed} falhados"
            ),
        )