"""Trích xuất source từ chunks.

Module này cung cấp function để trích xuất danh sách sources duy nhất từ
các chunks đã được retrieve. Mỗi source chỉ xuất hiện một lần trong kết quả,
bất kể có bao nhiêu chunks từ source đó.

Function chính:
- extract_sources: Trích xuất và deduplicate sources từ chunks
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def extract_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Trích xuất danh sách các source duy nhất từ chunks đã retrieve.
    
    Hàm này duyệt qua các chunks và trích xuất thông tin source, loại bỏ
    các source trùng lặp. Mỗi source chỉ xuất hiện một lần trong kết quả,
    bất kể có bao nhiêu chunks từ source đó.
    
    Args:
        chunks: Danh sách chunks đã được retrieve, mỗi chunk chứa metadata
            với source_reference, source_type, external_url, project_key
    
    Returns:
        List[Dict[str, Any]]: Danh sách các source duy nhất, mỗi source là
            dictionary chứa:
            - title: Tên source (từ source_reference hoặc heading)
            - type: Loại source (redmine_issue, redmine_wiki, etc.)
            - url: URL của source (nếu có)
            - project: Project key (nếu có)
    
    Note:
        - Chỉ trích xuất sources có source_label (source_reference hoặc heading)
        - Sources được deduplicate dựa trên source_label
        - Thứ tự trong kết quả theo thứ tự xuất hiện đầu tiên trong chunks
    """
    sources = []
    seen = set()
    
    for chunk in chunks:
        metadata = chunk.get('metadata', {})
        source_label = metadata.get('source_reference') or metadata.get('heading')
        
        if source_label and source_label not in seen:
            seen.add(source_label)
            sources.append({
                'title': source_label,
                'type': metadata.get('source_type'),
                'url': metadata.get('external_url'),
                'project': metadata.get('project_key'),
            })
    
    return sources

