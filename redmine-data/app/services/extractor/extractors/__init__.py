"""Các extractor file.

Module này chứa các extractors cho các file formats khác nhau:
- extract_pdf: Trích xuất text từ PDF files (sử dụng pdfplumber và PyPDF2)
- extract_docx: Trích xuất text và metadata từ DOCX files
- extract_text: Trích xuất text từ plain text files
- extract_markdown: Trích xuất text từ Markdown files
- extract_json: Trích xuất text từ JSON files (format thành readable text)
- extract_html: Trích xuất text từ HTML files (sử dụng BeautifulSoup)
- extract_with_tika: Fallback extractor sử dụng Apache Tika cho các format khác

Mỗi extractor trả về dictionary với 'text' và 'metadata' fields.
Tika extractor được sử dụng như fallback cho các format không được hỗ trợ trực tiếp.
"""
from app.services.extractor.extractors.pdf_extractor import extract_pdf
from app.services.extractor.extractors.docx_extractor import extract_docx
from app.services.extractor.extractors.text_extractor import (
    extract_text,
    extract_markdown,
    extract_json,
    extract_html
)
from app.services.extractor.extractors.tika_extractor import extract_with_tika

__all__ = [
    'extract_pdf',
    'extract_docx',
    'extract_text',
    'extract_markdown',
    'extract_json',
    'extract_html',
    'extract_with_tika'
]

