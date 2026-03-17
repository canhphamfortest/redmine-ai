"""Trích xuất PDF.

Module này cung cấp function để trích xuất text từ PDF files:
- extract_pdf: Trích xuất text và metadata từ PDF

Sử dụng cả pdfplumber và PyPDF2 để đảm bảo extraction tốt nhất:
- pdfplumber: Ưu tiên sử dụng, tốt hơn cho text extraction
- PyPDF2: Fallback nếu pdfplumber thất bại
"""
import logging
from typing import Dict, Any
from PyPDF2 import PdfReader
import pdfplumber

logger = logging.getLogger(__name__)


def extract_pdf(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung text và metadata từ file PDF.
    
    Hàm này sử dụng nhiều phương pháp để trích xuất PDF, với fallback
    tự động nếu phương pháp đầu tiên thất bại:
    1. Thử pdfplumber trước (tốt hơn cho bảng và layout phức tạp)
    2. Fallback về PyPDF2 nếu pdfplumber thất bại
    
    Args:
        file_path: Đường dẫn đến file PDF cần trích xuất (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): Nội dung text đã trích xuất từ tất cả các trang
            - metadata (dict): Metadata của PDF (title, author, etc.)
            - page_count (int): Số lượng trang trong PDF
    
    Raises:
        Exception: Nếu cả hai phương pháp đều thất bại
    
    Note:
        - pdfplumber thường tốt hơn cho PDF có bảng hoặc layout phức tạp
        - PyPDF2 là fallback đơn giản hơn nhưng có thể bỏ sót một số nội dung
        - Content được strip() để loại bỏ whitespace thừa
    """
    try:
        # Thử pdfplumber trước (tốt hơn cho bảng)
        with pdfplumber.open(file_path) as pdf:
            content = ""
            for page in pdf.pages:
                content += page.extract_text() or ""
            
            return {
                'content': content.strip(),
                'metadata': pdf.metadata or {},
                'page_count': len(pdf.pages)
            }
    except Exception as e1:
        logger.warning(f"pdfplumber failed, trying PyPDF2: {e1}")
        
        # Fallback sang PyPDF2
        try:
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                content = ""
                for page in reader.pages:
                    content += page.extract_text() or ""
                
                return {
                    'content': content.strip(),
                    'metadata': reader.metadata or {},
                    'page_count': len(reader.pages)
                }
        except Exception as e2:
            logger.error(f"PyPDF2 also failed: {e2}")
            raise

