from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from loguru import logger

class DFPParser:
    """Parser específico para documentos financeiros, utilizando a biblioteca Docling para extrair texto e estrutura de PDFs."""

    # Configurações do pipeline de extração de PDFs, com OCR opcional e extração de estrutura de tabelas
    def __init__(self, do_ocr: bool = False, do_table_structure: bool = True):
        pipeline_options = PdfPipelineOptions(
            do_ocr=do_ocr,
            do_table_structure=do_table_structure,
        )
        pipeline_options.table_structure_options.do_cell_matching = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    # Método principal para processar um PDF e extrair seu conteúdo em formato estruturado, incluindo texto em markdown e tabelas
    def parse(self, pdf_path: Path) -> dict[str, Any]:
        if not pdf_path.exists():
            logger.error(f"Arquivo PDF não encontrado: {pdf_path}")
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")
        
        # Tenta converter o PDF usando o DocumentConverter do Docling, capturando erros e logando o progresso
        try:
            logger.info(f"Iniciando parsing do PDF: {pdf_path}")
            result = self.converter.convert(str(pdf_path))
            doc = result.document
            logger.info(f"Parsing concluído para o PDF: {pdf_path}")
        except Exception as e:
            logger.error(f"Erro ao processar o PDF {pdf_path}: {e}")
            raise e
        
        # Exporta o conteúdo do PDF para markdown, que pode ser útil para análises baseadas em texto, e armazena as tabelas 
        # extraídas em formato de dicionário, incluindo a página de origem e a representação em markdown da tabela
        markdown = doc.export_to_markdown()
   
        # Itera sobre as tabelas extraídas do PDF e armazena seu conteúdo em formato de dicionário, incluindo a página de origem, 
        # o conteúdo da tabela em formato de lista de registros, e a representação em markdown da tabela
        tables = []        
        for table in doc.tables:
            tables.append({
                "page": table.prov[0].page_no if table.prov else None,
                "content": table.export_to_dataframe().to_dict(orient="records"),
                "markdown": table.export_to_markdown()
            })
        
        logger.info(f"Extração de tabelas concluída para o PDF: {pdf_path}, total de tabelas extraídas: {len(tables)}")

        # 
        return {
            "markdown": markdown,
            "tables": tables,
            "page_count": len(doc.pages),
            "raw_doc": doc
        }




