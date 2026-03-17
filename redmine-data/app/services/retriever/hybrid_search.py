"""Hybrid search kết hợp Vector Search và Keyword Search.

Module này cung cấp hybrid search sử dụng Reciprocal Rank Fusion (RRF):
- merge_with_rrf: Merge kết quả từ vector và keyword search
- hybrid_search: Main function thực hiện hybrid search

Hybrid search kết hợp ưu điểm của cả hai phương pháp:
- Vector Search: Tìm kiếm semantic (hiểu ngữ nghĩa)
- Keyword Search: Tìm kiếm exact match (từ khóa chính xác)
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.retriever.keyword_search import keyword_search
from app.services.retriever.vector_search import vector_search_by_query

logger = logging.getLogger(__name__)

# Constants
HYBRID_CANDIDATES = 50  # Số candidates từ mỗi search method
RRF_K = 60  # RRF constant (standard value, higher = more weight to lower ranks)


def merge_with_rrf(
    vector_results: List[Dict[str, Any]],
    keyword_results: List[Dict[str, Any]],
    k: int = RRF_K
) -> List[Dict[str, Any]]:
    """Merge kết quả từ vector search và keyword search bằng RRF.
    
    Reciprocal Rank Fusion (RRF) kết hợp kết quả từ nhiều nguồn bằng cách
    tính điểm dựa trên vị trí (rank) thay vì score gốc. Điều này giải quyết
    vấn đề score từ các nguồn khác nhau không cùng scale.
    
    Formula: RRF_score(d) = Σ 1/(k + rank_i(d))
    
    Chunks xuất hiện ở cả vector và keyword results sẽ có RRF score cao hơn.
    
    Args:
        vector_results: Kết quả từ vector search (sorted by similarity_score)
        keyword_results: Kết quả từ keyword search (sorted by fts_rank)
        k: RRF constant (mặc định: 60). K cao hơn = weight nhiều hơn cho ranks thấp
    
    Returns:
        List[Dict[str, Any]]: Merged results sorted by RRF score, mỗi chunk chứa:
            - chunk_id: UUID của chunk (str)
            - text: Nội dung chunk (str)
            - chunk_type: Loại chunk (str)
            - rrf_score: Điểm RRF tổng hợp (float)
            - similarity_score: Điểm từ vector search nếu có (float, optional)
            - fts_rank: Điểm từ keyword search nếu có (float, optional)
            - metadata: Dictionary metadata
    
    Example:
        >>> vector = [{'chunk_id': 'a', ...}, {'chunk_id': 'b', ...}]
        >>> keyword = [{'chunk_id': 'b', ...}, {'chunk_id': 'c', ...}]
        >>> merged = merge_with_rrf(vector, keyword)
        # chunk 'b' will have highest RRF score (appears in both)
    """
    scores: Dict[str, float] = {}
    chunk_data: Dict[str, Dict[str, Any]] = {}
    
    # Score từ vector search
    for rank, result in enumerate(vector_results, 1):
        chunk_id = result['chunk_id']
        rrf_contribution = 1 / (k + rank)
        scores[chunk_id] = scores.get(chunk_id, 0) + rrf_contribution
        
        # Store chunk data (ưu tiên vector search data)
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = result.copy()
            chunk_data[chunk_id]['vector_rank'] = rank
    
    # Score từ keyword search
    for rank, result in enumerate(keyword_results, 1):
        chunk_id = result['chunk_id']
        rrf_contribution = 1 / (k + rank)
        scores[chunk_id] = scores.get(chunk_id, 0) + rrf_contribution
        
        # Store chunk data nếu chưa có (từ vector search)
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = result.copy()
        
        # Track keyword rank
        chunk_data[chunk_id]['keyword_rank'] = rank
        
        # Copy fts_rank nếu có
        if 'fts_rank' in result:
            chunk_data[chunk_id]['fts_rank'] = result['fts_rank']
    
    # Sort theo RRF score giảm dần
    sorted_chunk_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    # Build final results
    results = []
    for chunk_id in sorted_chunk_ids:
        result = chunk_data[chunk_id].copy()
        result['rrf_score'] = scores[chunk_id]
        results.append(result)
    
    logger.debug(
        f"RRF merge: {len(vector_results)} vector + {len(keyword_results)} keyword "
        f"= {len(results)} unique chunks"
    )
    
    return results


def hybrid_search(
    query: str,
    db: Session,
    top_k: int,
    similarity_threshold: float
) -> List[Dict[str, Any]]:
    """Hybrid search kết hợp Vector Search và Keyword Search.
    
    Hàm này thực hiện cả vector search và keyword search song song,
    sau đó merge kết quả bằng RRF để lấy top_k chunks tốt nhất.
    
    Flow:
    1. Vector Search: Tìm HYBRID_CANDIDATES chunks bằng semantic similarity
    2. Keyword Search: Tìm HYBRID_CANDIDATES chunks bằng full-text search
    3. RRF Merge: Kết hợp và sắp xếp theo RRF score
    4. Return top_k results
    
    Args:
        query: Chuỗi query từ người dùng (string)
        db: Database session
        top_k: Số lượng kết quả cuối cùng (mặc định từ config: 5)
        similarity_threshold: Ngưỡng similarity cho vector search
    
    Returns:
        List[Dict[str, Any]]: Top_k chunks sorted by RRF score, mỗi chunk chứa:
            - chunk_id: UUID của chunk (str)
            - text: Nội dung chunk (str)
            - chunk_type: Loại chunk (str)
            - rrf_score: Điểm RRF tổng hợp (float)
            - similarity_score: Điểm từ vector search nếu có (float, optional)
            - fts_rank: Điểm từ keyword search nếu có (float, optional)
            - metadata: Dictionary metadata
    
    Note:
        - Nếu keyword search không có kết quả (query chỉ có stopwords),
          fallback về vector-only results
        - Nếu vector search không có kết quả, trả về keyword-only results
        - Nếu cả hai không có kết quả, trả về empty list
    """
    logger.info(f"Hybrid search for query: '{query[:100]}...' (top_k={top_k})")
    
    # Vector Search - lấy HYBRID_CANDIDATES chunks
    # Sử dụng HYBRID_CANDIDATES thay vì top_k để có pool lớn hơn cho merge
    vector_results = vector_search_by_query(
        query=query,
        db=db,
        top_k=HYBRID_CANDIDATES,
        similarity_threshold=similarity_threshold
    )
    logger.debug(f"Vector search returned {len(vector_results)} results")
    
    # Keyword Search - lấy HYBRID_CANDIDATES chunks
    keyword_results = keyword_search(
        query=query,
        db=db,
        limit=HYBRID_CANDIDATES
    )
    logger.debug(f"Keyword search returned {len(keyword_results)} results")
    
    # Edge cases handling
    if not vector_results and not keyword_results:
        logger.info("Both vector and keyword search returned no results")
        return []
    
    if not keyword_results:
        logger.info("Keyword search returned no results, using vector-only")
        return vector_results[:top_k]
    
    if not vector_results:
        logger.info("Vector search returned no results, using keyword-only")
        # Convert keyword results format to match expected output
        return _convert_keyword_to_standard_format(keyword_results[:top_k])
    
    # Merge với RRF
    merged_results = merge_with_rrf(vector_results, keyword_results)
    
    logger.info(
        f"Hybrid search complete: {len(merged_results)} total, returning top {top_k}"
    )
    
    return merged_results[:top_k]


def _convert_keyword_to_standard_format(
    keyword_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Convert keyword results sang standard format (thêm similarity_score = 0).
    
    Khi chỉ có keyword results (không có vector), cần convert format
    để compatible với downstream code expecting similarity_score.
    
    Args:
        keyword_results: Results từ keyword search
    
    Returns:
        List với similarity_score added (set to 0)
    """
    results = []
    for result in keyword_results:
        converted = result.copy()
        if 'similarity_score' not in converted:
            converted['similarity_score'] = 0.0
        if 'distance' not in converted:
            converted['distance'] = 1.0
        results.append(converted)
    return results

