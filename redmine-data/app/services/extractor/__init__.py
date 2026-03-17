"""Module service trích xuất nội dung.

Module này cung cấp content extraction service để trích xuất text từ các file formats:
- ContentExtractor: Class chính thực hiện extraction
- extractor: Singleton instance được sử dụng trong toàn bộ ứng dụng

Hỗ trợ các định dạng:
- PDF: Sử dụng pdfplumber và PyPDF2
- DOCX: Sử dụng python-docx
- TXT, MD, JSON, HTML: Text-based extraction
- Apache Tika: Fallback extractor cho các format khác

Extracted content được sử dụng để tạo chunks và embeddings.
"""
from app.services.extractor.extractor import extractor, ContentExtractor

__all__ = ['extractor', 'ContentExtractor']

