from collections import defaultdict
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
        
        markdown = doc.export_to_markdown()

        tables = []
        for table in doc.tables:
            tables.append({
                "page": table.prov[0].page_no if table.prov else None,
                "content": table.export_to_dataframe(doc=doc).to_dict(orient="records"),
                "markdown": table.export_to_markdown(doc=doc)
            })

        logger.info(f"Extração de tabelas concluída para o PDF: {pdf_path}, total de tabelas extraídas: {len(tables)}")

        # Extrai texto agrupado por página usando a estrutura nativa do Docling.
        # Cada TextItem já sabe em qual página está via item.prov[0].page_no — sem heurísticas.
        page_texts: dict[int, list[str]] = defaultdict(list)
        for text_item in doc.texts:
            if not text_item.text or not text_item.text.strip():
                continue
            if not text_item.prov:
                continue
            page_no = text_item.prov[0].page_no
            page_texts[page_no].append(text_item.text.strip())

        pages = [
            {"page_no": pn, "text": "\n\n".join(texts)}
            for pn, texts in sorted(page_texts.items())
        ]
        logger.info(f"Extração de texto por página concluída: {len(pages)} páginas com conteúdo.")

        return {
            "markdown": markdown,
            "tables": tables,
            "pages": pages,
            "page_count": len(doc.pages),
            "raw_doc": doc
        }




