"""Định dạng kết quả cho vector search.

Module này cung cấp functions để format kết quả từ vector search queries:
- format_search_result: Format một database row thành dictionary chuẩn
- format_search_results: Format nhiều rows và sắp xếp theo similarity score

Tăng điểm similarity cho issue_metadata chunks để ưu tiên chúng trong kết quả.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def format_search_result(row, include_source_id: bool = False) -> Dict[str, Any]:
    """Định dạng một dòng kết quả tìm kiếm từ database row.
    
    Hàm này chuyển đổi database row thành dictionary format chuẩn cho API response.
    Tăng điểm similarity cho issue_metadata chunks để ưu tiên chúng trong kết quả.
    
    Args:
        row: Database row object từ vector search query, chứa:
            - id: Chunk ID
            - text_content: Nội dung chunk
            - chunk_type: Loại chunk
            - similarity: Điểm similarity từ vector search
            - distance: Khoảng cách vector
            - source_reference, source_type, external_url, project_key, language,
              heading_title, author_name, page_number: Metadata từ joins
            - source_id: Source ID (optional, nếu include_source_id=True)
        include_source_id: Có bao gồm source_id trong metadata không (mặc định: False)
    
    Returns:
        Dict[str, Any]: Dictionary kết quả đã định dạng:
            - chunk_id: UUID của chunk (str)
            - text: Nội dung chunk (str)
            - chunk_type: Loại chunk (str)
            - similarity_score: Điểm similarity (float, 0-1, đã boost cho issue_metadata)
            - distance: Khoảng cách vector (float)
            - metadata: Dictionary metadata (Dict):
                - source_reference: Reference đến source (str)
                - source_type: Loại source (str)
                - external_url: URL ngoài (str, optional)
                - project_key: Project key (str, optional)
                - language: Mã ngôn ngữ (str, optional)
                - heading: Tiêu đề heading (str, optional)
                - author: Tên tác giả (str, optional)
                - page: Số trang (int, optional)
                - source_id: Source ID (str, optional, nếu include_source_id=True)
    
    Note:
        - Issue metadata chunks được boost 10% similarity score (max 1.0)
        - Giúp ưu tiên metadata chunks trong kết quả tìm kiếm
    """
    similarity = float(row.similarity)
    chunk_type = row.chunk_type
    
    # Tăng điểm issue_metadata chunks 10% để ưu tiên chúng
    if chunk_type == 'issue_metadata':
        similarity = min(1.0, similarity * 1.1)
    
    result = {
        'chunk_id': str(row.id),
        'text': row.text_content,
        'chunk_type': chunk_type,
        'similarity_score': similarity,
        'distance': float(row.distance),
        'metadata': {
            'source_reference': row.source_reference,
            'source_type': row.source_type,
            'external_url': row.external_url,
            'project_key': row.project_key,
            'language': row.language,
            'heading': row.heading_title,
            'author': row.author_name,
            'page': row.page_number,
        }
    }
    
    # Thêm source_id nếu được yêu cầu
    if include_source_id and hasattr(row, 'source_id'):
        result['metadata']['source_id'] = str(row.source_id)
    
    return result


def format_search_results(rows: List, include_source_id: bool = False) -> List[Dict[str, Any]]:
    """Định dạng nhiều dòng kết quả tìm kiếm.
    
    Hàm này format tất cả rows từ vector search query và sắp xếp lại theo
    similarity score (sau khi boost) để đảm bảo thứ tự đúng.
    
    Args:
        rows: Danh sách database row objects từ vector search query (List)
        include_source_id: Có bao gồm source_id trong metadata không (mặc định: False)
    
    Returns:
        List[Dict[str, Any]]: Danh sách các dictionary kết quả đã định dạng,
                              được sắp xếp theo similarity_score giảm dần
    
    Note:
        - Mỗi row được format bằng format_search_result()
        - Kết quả được sắp xếp lại theo similarity_score sau khi boost
        - Đảm bảo issue_metadata chunks có priority cao hơn sau khi boost
    """
    results = []
    for row in rows:
        results.append(format_search_result(row, include_source_id=include_source_id))
    
    # Sắp xếp lại theo điểm similarity đã tăng
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    return results

