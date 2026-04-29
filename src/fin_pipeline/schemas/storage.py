from pydantic import BaseModel, Field

from fin_pipeline.schemas.document import Chunk

class EmbeddedChunk(BaseModel):
    """Modelo de dados para um chunk de texto que foi processado e convertido em um vetor de embedding, contendo o chunk original,
      o vetor denso gerado pelo modelo de embedding, e os vetores sparse BM25 para recuperação baseada em palavras-chave."""

    # O chunk original de texto, incluindo seus metadados, que foi processado para gerar os vetores de embedding.
    chunk: Chunk

    # Vetor denso de embedding gerado pelo modelo OpenAI text-embedding-3-large, com 3072 dimensões
    dense_vector: list[float] = Field(
        description="Dense Embedding OpenAI text-embedding-3-large (3072 dimensões)"
    )

    # Vetores sparse BM25 para recuperação baseada em palavras-chave, onde sparse_indices contém os índices das palavras-chave
    #  relevantes e sparse_values contém os valores correspondentes de relevância para cada índice.
    sparse_indices: list[float] = Field(
        description="BM25 sparse vector indices"
    )

    # Vetores sparse BM25 para recuperação baseada em palavras-chave, onde sparse_indices contém os índices das palavras-chave
    sparse_values: list[float] = Field(
        description="Valores de vetores sparse BM25 correspondentes aos índices"
    )

    # Validação para garantir que os vetores sparse_indices e sparse_values tenham o mesmo comprimento, 
    # já que cada índice deve ter um valor correspondente de relevância.
    def model_post_init(self, context) -> None:
        if len(self.sparse_indices) != len(self.sparse_values):
            raise ValueError(
                f"Sparse indices ({len(self.sparse_indices)}) e valores: ({len(self.sparse_values)}) devem ter o mesmo comprimento"
            )
        
class IndexingStats(BaseException):
    """Modelo de dados para as estatísticas do processo de indexação dos chunks no Qdrant, 
    contendo o número total de chunks processados, o número de chunks que foram indexados com sucesso,
    o número de chunks que falharam durante o processamento ou indexação, 
    o nome da coleção no Qdrant onde os chunks foram indexados, e a duração total do processo de indexação em segundos."""
    total_chunk: int = Field(description="Número total de chunks processados para indexação")
    successful: int = Field(description="Número de chunks que foram processados e indexados com sucesso")
    failed: int = Field(description="Número de chunks que falharam durante o processamento ou indexação, seja por erros de processamento, erros de comunicação com o Qdrant, ou rejeição de chunks pelo Qdrant devido a limitações de tamanho ou conteúdo inadequado.")
    colection_name: str = Field(description="Nome da coleção no Qdrant onde os chunks foram indexados")
    duration_seconds: float = Field(description="Duração total do processo de indexação, desde o início do processamento dos chunks até a confirmação de que todos os chunks foram indexados ou falharam, expresso em segundos.")

    @property
    def success_rate(self) -> float:
        """Calcula a taxa de sucesso do processo de indexação, dividindo o número de chunks bem-sucedidos
          pelo número total de chunks processados, e retornando o resultado como um valor entre 0.0 (sem sucesso)
           e 1.0 (sucesso total). Se nenhum chunk foi processado, retorna 0.0 para evitar divisão por zero."""
        if self.total_chunk == 0:
            return 0.0
        return self.successful / self.total_chunk