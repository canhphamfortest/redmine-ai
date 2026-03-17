"""Trích xuất DOCX.

Module này cung cấp function để trích xuất text từ DOCX files:
- extract_docx: Trích xuất text và metadata từ Microsoft Word documents

Sử dụng python-docx library để đọc paragraphs và core properties.
Trả về text content và metadata (author, dates, page count).
"""
from typing import Dict, Any
from docx import Document as DocxDocument


def extract_docx(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung text và metadata từ file DOCX (Microsoft Word).
    
    Hàm này sử dụng python-docx library để đọc file DOCX và trích xuất:
    - Tất cả các đoạn văn (paragraphs) thành text
    - Metadata từ core properties (author, dates, title)
    
    Args:
        file_path: Đường dẫn đến file DOCX cần trích xuất (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): Nội dung text từ tất cả các paragraphs, nối bằng newline
            - metadata (dict): Dictionary chứa author, created, modified, title
                (chỉ các fields có giá trị)
            - page_count (int): Số lượng sections trong document
    
    Note:
        - Chỉ trích xuất text từ paragraphs, không bao gồm tables, images
        - Metadata values được convert sang string
        - page_count thực chất là số sections, không phải số trang thực tế
    """
    doc = DocxDocument(file_path)
    
    # Trích xuất các đoạn văn
    content = "\n".join([para.text for para in doc.paragraphs])
    
    # Trích xuất metadata
    metadata = {
        'author': doc.core_properties.author,
        'created': doc.core_properties.created,
        'modified': doc.core_properties.modified,
        'title': doc.core_properties.title,
    }
    
    return {
        'content': content.strip(),
        'metadata': {k: str(v) for k, v in metadata.items() if v},
        'page_count': len(doc.sections)
    }

