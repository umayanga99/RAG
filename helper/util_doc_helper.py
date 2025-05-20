from pathlib import Path
from typing import List
from llama_index.core import Document
import fitz  # PyMuPDF

# 1. Extract text from each page of a PDF and build Document objects with metadata
def build_docs_with_metadata(pdf_path: str) -> List[Document]:
    docs = []

    # 1.1 Open the PDF
    doc = fitz.open(pdf_path)

    # 1.2 Iterate over all pages
    for i, page in enumerate(doc):
        text = page.get_text()

        # 1.3 Only process non-empty pages
        if text.strip():
            docs.append(Document(
                text=text,
                metadata={
                    "source": "pdf",
                    "filename": Path(pdf_path).name,
                    "page": i + 1,
                    "type": "page"
                }
            ))

    # 1.4 Return the list of Document objects
    return docs
