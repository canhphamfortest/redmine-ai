"""Service trích xuất nội dung chính.

Module này cung cấp ContentExtractor class để trích xuất text từ các file formats:
- ContentExtractor: Class chính tự động phát hiện format và chọn extractor phù hợp
- extractor: Singleton instance được sử dụng trong toàn bộ ứng dụng

Hỗ trợ nhiều định dạng: PDF, DOCX, TXT, MD, JSON, HTML.
Fallback về Apache Tika cho các định dạng không được hỗ trợ trực tiếp.
"""
import logging
import mimetypes
from pathlib import Path
from typing import Dict, Any

from app.services.extractor.extractors import (
    extract_pdf,
    extract_docx,
    extract_text,
    extract_markdown,
    extract_json,
    extract_html,
    extract_with_tika
)

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Trích xuất nội dung văn bản từ các định dạng file khác nhau.
    
    Class này cung cấp interface thống nhất để trích xuất text từ nhiều
    định dạng file khác nhau. Tự động phát hiện định dạng và chọn extractor
    phù hợp. Hỗ trợ fallback về Apache Tika cho các định dạng không được
    hỗ trợ trực tiếp.
    
    Attributes:
        supported_formats: Dictionary mapping file extensions đến extractor functions
    """
    
    def __init__(self):
        """Khởi tạo ContentExtractor với các extractors được hỗ trợ."""
        self.supported_formats = {
            'pdf': extract_pdf,
            'docx': extract_docx,
            'doc': extract_with_tika,  # Định dạng DOC cũ sử dụng Tika
            'txt': extract_text,
            'md': extract_markdown,
            'json': extract_json,
            'html': extract_html,
        }
    
    def extract(self, file_path: str, mime_type: str = None) -> Dict[str, Any]:
        """Trích xuất nội dung text và metadata từ file.
        
        Hàm này tự động phát hiện định dạng file dựa trên extension hoặc
        MIME type, sau đó gọi extractor phù hợp. Nếu không tìm thấy extractor
        cụ thể, sẽ fallback về Apache Tika.
        
        Quy trình:
        1. Phát hiện file extension từ đường dẫn
        2. Phát hiện MIME type (nếu chưa được cung cấp)
        3. Chọn extractor dựa trên extension
        4. Gọi extractor và thêm thông tin file extension, MIME type vào kết quả
        
        Args:
            file_path: Đường dẫn đến file cần trích xuất (string)
            mime_type: MIME type của file (tùy chọn).
                Nếu None, sẽ tự động phát hiện bằng mimetypes.guess_type()
        
        Returns:
            Dict[str, Any]: Dictionary chứa kết quả trích xuất:
                - content (str): Nội dung text đã trích xuất
                - metadata (dict): Metadata của file (author, dates, etc.)
                - page_count (int, optional): Số trang (cho PDF, DOCX)
                - file_extension (str): Extension của file
                - mime_type (str): MIME type của file
                - error (str, optional): Thông báo lỗi nếu trích xuất thất bại
        
        Note:
            - Nếu file không được hỗ trợ trực tiếp, sẽ sử dụng Tika extractor
            - Nếu có lỗi, sẽ trả về dictionary với content rỗng và error message
            - Một số file có thể không có page_count trong metadata
        """
        try:
            path = Path(file_path)
            
            # Phát hiện định dạng
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_path)
            
            extension = path.suffix.lower().lstrip('.')
            
            # Chọn extractor
            extractor = self.supported_formats.get(extension)
            
            if not extractor:
                logger.warning(f"No specific extractor for {extension}, using Tika")
                return extract_with_tika(file_path)
            
            result = extractor(file_path)
            result['file_extension'] = extension
            result['mime_type'] = mime_type
            
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed for {file_path}: {e}")
            return {
                'content': '',
                'metadata': {},
                'error': str(e)
            }


# Instance singleton
extractor = ContentExtractor()

