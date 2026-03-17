"""Trích xuất dựa trên Tika cho các định dạng không được hỗ trợ.

Module này cung cấp function để trích xuất text bằng Apache Tika:
- extract_with_tika: Fallback extractor cho các format không được hỗ trợ trực tiếp

Apache Tika hỗ trợ rất nhiều định dạng file (Office documents, images với OCR, etc.)
nhưng chậm hơn các extractors chuyên biệt. Được sử dụng như fallback option.
"""
from typing import Dict, Any
from tika import parser as tika_parser


def extract_with_tika(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung từ file bằng Apache Tika (fallback cho các định dạng không được hỗ trợ).
    
    Hàm này sử dụng Apache Tika để trích xuất text và metadata từ các định dạng
    file không được hỗ trợ trực tiếp bởi các extractors khác. Tika hỗ trợ rất
    nhiều định dạng file (DOC, RTF, ODT, XLS, PPT, etc.).
    
    Args:
        file_path: Đường dẫn đến file cần trích xuất (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): Nội dung text đã được trích xuất (hoặc empty string)
            - metadata (dict): Metadata của file từ Tika (có thể rất nhiều fields)
    
    Note:
        - Tika cần được cài đặt và chạy (có thể là local server hoặc remote)
        - Tika có thể xử lý rất nhiều định dạng nhưng có thể chậm hơn các extractors chuyên biệt
        - Metadata từ Tika có thể chứa nhiều fields khác nhau tùy theo loại file
        - Nếu Tika không thể trích xuất, content sẽ là empty string
    """
    parsed = tika_parser.from_file(file_path)
    
    return {
        'content': (parsed.get('content') or '').strip(),
        'metadata': parsed.get('metadata', {}),
    }

