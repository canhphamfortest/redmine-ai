"""Triển khai vector search.

Module này cung cấp các helper functions để thực hiện vector search trong PostgreSQL:
- Query building: Xây dựng SQL queries với pgvector operators
- Threshold management: Quản lý similarity thresholds và fallback
- Result execution: Thực thi queries và format results
- Validation: Validate embedding dimensions và format

Sử dụng pgvector extension trong PostgreSQL để thực hiện vector similarity search
bằng cosine distance. Hỗ trợ fallback threshold nếu không tìm đủ kết quả.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.embedder import embedder
from app.services.retriever.result_formatter import format_search_results

logger = logging.getLogger(__name__)

# Các ngưỡng thấp hơn để retry fallback
LOWER_THRESHOLDS = [0.3, 0.2, 0.1, 0.05]

# Số lượng candidates mặc định cho search
# Tối ưu: Lấy gấp 2-3 lần top_k, tối thiểu 20 để đảm bảo có đủ results sau filter
DEFAULT_CANDIDATES = 20
CANDIDATE_MULTIPLIER = 3  # Lấy candidates = top_k * 3


def vector_search_by_query(
    query: str,
    db: Session,
    top_k: int,
    similarity_threshold: float,
    project_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Vector search bằng văn bản truy vấn
    
    Args:
        query: Văn bản truy vấn tìm kiếm
        db: Database session
        top_k: Số lượng kết quả trả về
        similarity_threshold: Ngưỡng similarity tối thiểu
        
    Returns:
        Danh sách các chunk liên quan kèm metadata và điểm số
    """
    try:
        # Tạo embedding cho query
        embedding_start = time.time()
        logger.debug(f"Generating embedding for query: {query[:100]}...")
        query_embedding = embedder.embed_text(query)
        embedding_time_ms = int((time.time() - embedding_start) * 1000)
        logger.debug(f"Embedding generation took {embedding_time_ms}ms")
        
        # Xác thực kích thước embedding
        _validate_embedding_dimension(query_embedding)
        
        # Định dạng embedding thành string
        embedding_str = _format_embedding_to_string(query_embedding)
        
        # Xây dựng SQL query
        sql_query = _build_vector_search_query(embedding_str, include_source_id=False, project_ids=project_ids)
        
        params = {
            'limit': max(DEFAULT_CANDIDATES, top_k * 5),
            'threshold': similarity_threshold
        }
        
        # Thực thi query và lấy kết quả
        sql_start = time.time()
        results = _execute_vector_search_query(sql_query, params, top_k, db, include_source_id=False)
        sql_time_ms = int((time.time() - sql_start) * 1000)
        logger.debug(f"Vector SQL query took {sql_time_ms}ms, embedding: {embedding_time_ms}ms")
        
        # Thử lại với threshold thấp hơn nếu không có kết quả
        if not results:
            fallback_start = time.time()
            results = _search_with_fallback_threshold(
                sql_query, params, similarity_threshold, top_k, db, include_source_id=False
            )
            fallback_time_ms = int((time.time() - fallback_start) * 1000)
            if fallback_time_ms > 0:
                logger.debug(f"Fallback threshold search took {fallback_time_ms}ms")
        
        return results
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


def vector_search_by_embedding(
    embedding_vector: List[float],
    db: Session,
    top_k: int,
    similarity_threshold: float,
    exclude_source_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Vector search bằng embedding vector trực tiếp
    
    Args:
        embedding_vector: Vector embedding để tìm kiếm
        db: Database session
        top_k: Số lượng kết quả trả về
        similarity_threshold: Ngưỡng similarity tối thiểu
        exclude_source_ids: Danh sách source ID để loại trừ khỏi kết quả
        
    Returns:
        Danh sách các chunk liên quan kèm metadata và điểm số
    """
    try:
        # Xác thực kích thước embedding
        _validate_embedding_dimension(embedding_vector)
        
        # Định dạng embedding thành string
        embedding_str = _format_embedding_to_string(embedding_vector)
        
        # Xây dựng SQL query với exclude_source_ids
        sql_query, params = _build_vector_search_query_with_excludes(
            embedding_str, exclude_source_ids, include_source_id=True
        )
        
        params['limit'] = max(DEFAULT_CANDIDATES, top_k * 5)
        params['threshold'] = similarity_threshold
        
        # Thực thi query và lấy kết quả
        results = _execute_vector_search_query(sql_query, params, top_k, db, include_source_id=True)
        
        # Thử lại với threshold thấp hơn nếu không có kết quả
        if not results:
            results = _search_with_fallback_threshold(
                sql_query, params, similarity_threshold, top_k, db, include_source_id=True
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Vector search by embedding failed: {e}")
        return []


def _validate_embedding_dimension(embedding: List[float]) -> None:
    """Xác thực kích thước embedding vector khớp với kích thước mong đợi.
    
    Hàm này kiểm tra xem embedding vector có đúng kích thước không. Kích thước
    phải khớp với embedding_dim của embedder service. Nếu không khớp, sẽ raise
    ValueError để tránh lỗi khi thực thi SQL query.
    
    Args:
        embedding: Embedding vector cần kiểm tra (List[float])
    
    Raises:
        ValueError: Nếu kích thước embedding không khớp với kích thước mong đợi
    
    Note:
        - Kích thước mong đợi được lấy từ embedder.embedding_dim
        - Lỗi này thường xảy ra khi sử dụng sai model hoặc embedding bị corrupt
    """
    expected_dim = embedder.embedding_dim
    actual_dim = len(embedding)
    
    if actual_dim != expected_dim:
        logger.error(f"Embedding dimension mismatch! Expected {expected_dim}, got {actual_dim}")
        raise ValueError(f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}")


def _format_embedding_to_string(embedding: List[float]) -> str:
    """Định dạng embedding vector thành chuỗi vector PostgreSQL.
    
    Hàm này chuyển đổi list các số float thành string format mà PostgreSQL
    pgvector extension có thể hiểu. Format: '[val1,val2,val3,...]'
    
    Args:
        embedding: Embedding vector dạng list các số float
    
    Returns:
        str: String representation của vector theo format PostgreSQL
    
    Example:
        >>> _format_embedding_to_string([0.1, 0.2, 0.3])
        '[0.1,0.2,0.3]'
    """
    return '[' + ','.join(map(str, embedding)) + ']'


def _build_vector_search_query(embedding_str: str, include_source_id: bool = False, project_ids: Optional[List[int]] = None) -> str:
    """Xây dựng SQL query cho vector similarity search sử dụng pgvector.
    
    Hàm này tạo SQL query sử dụng pgvector operator (<=>) để tìm các chunks
    có embedding gần nhất với query embedding. Query sử dụng cosine distance
    và chuyển đổi thành similarity score (1 - distance).
    
    Query structure:
    1. Subquery ranked: Lọc embeddings theo status và similarity threshold, order và limit sớm
    2. Join với chunk và source: Chỉ join với các embeddings đã được filter
    
    Args:
        embedding_str: Embedding vector đã được format thành string PostgreSQL
        include_source_id: Có bao gồm source_id trong SELECT không (mặc định: False)
    
    Returns:
        str: SQL query string để thực thi
    
    Note:
        - Sử dụng pgvector operator <=> cho cosine distance
        - Tối ưu hóa bằng cách filter và limit sớm trước khi join
        - Chỉ lấy chunks có status='processed' và embeddings có status='active'
    """
    source_id_select = "s.id AS source_id," if include_source_id else ""
    
    return f"""
        SELECT
            c.id,
            c.text_content,
            c.chunk_type,
            c.heading_title,
            c.author_name,
            c.created_on,
            c.page_number,
            {source_id_select}
            s.external_id AS source_reference,
            s.source_type,
            s.external_url,
            s.project_key,
            s.language,
            ranked.distance,
            ranked.similarity
        FROM (
            SELECT 
                e.chunk_id,
                e.embedding <=> '{embedding_str}'::vector AS distance,
                1 - (e.embedding <=> '{embedding_str}'::vector) AS similarity
            FROM embedding e
            WHERE 
                e.status = 'active'
                AND (1 - (e.embedding <=> '{embedding_str}'::vector)) >= :threshold
            ORDER BY e.embedding <=> '{embedding_str}'::vector ASC
            LIMIT :limit
        ) ranked
        INNER JOIN chunk c ON c.id = ranked.chunk_id AND c.status = 'processed'
        INNER JOIN source s ON s.id = c.source_id
        {f"WHERE s.project_id IN ({','.join(map(str, project_ids))})" if project_ids and len(project_ids) > 0 else ""}
    """


def _build_vector_search_query_with_excludes(
    embedding_str: str,
    exclude_source_ids: Optional[List[str]],
    include_source_id: bool = False
) -> Tuple[str, Dict[str, Any]]:
    """Xây dựng SQL query cho vector search với khả năng loại trừ một số sources.
    
    Tương tự như _build_vector_search_query nhưng có thêm khả năng loại trừ
    các source IDs khỏi kết quả. Hữu ích khi muốn tìm kiếm các chunks từ
    sources khác với source hiện tại.
    
    Args:
        embedding_str: Embedding vector đã được format thành string PostgreSQL
        exclude_source_ids: Danh sách source IDs cần loại trừ (tùy chọn)
        include_source_id: Có bao gồm source_id trong SELECT không (mặc định: False)
    
    Returns:
        Tuple[str, Dict[str, Any]]: Tuple chứa:
            - SQL query string
            - Dictionary parameters cho query (bao gồm exclude placeholders)
    
    Note:
        - Nếu exclude_source_ids là None hoặc rỗng, query sẽ giống như không có exclude
        - Parameters sử dụng named placeholders để tránh SQL injection
        - Tối ưu hóa bằng cách filter và limit sớm trước khi join
    """
    source_id_select = "s.id AS source_id," if include_source_id else ""
    
    params = {}
    
    # Xây dựng phần loại trừ source ID trong JOIN nếu có
    exclude_join_condition = ""
    if exclude_source_ids:
        placeholders = ','.join([f':exclude_{i}' for i in range(len(exclude_source_ids))])
        exclude_join_condition = f" AND s.id NOT IN ({placeholders})"
        for i, source_id in enumerate(exclude_source_ids):
            params[f'exclude_{i}'] = str(source_id)
    
    sql_query = f"""
        SELECT
            c.id,
            c.text_content,
            c.chunk_type,
            c.heading_title,
            c.author_name,
            c.created_on,
            c.page_number,
            {source_id_select}
            s.external_id AS source_reference,
            s.source_type,
            s.external_url,
            s.project_key,
            s.language,
            ranked.distance,
            ranked.similarity
        FROM (
            SELECT 
                e.chunk_id,
                e.embedding <=> '{embedding_str}'::vector AS distance,
                1 - (e.embedding <=> '{embedding_str}'::vector) AS similarity
            FROM embedding e
            WHERE 
                e.status = 'active'
                AND (1 - (e.embedding <=> '{embedding_str}'::vector)) >= :threshold
            ORDER BY e.embedding <=> '{embedding_str}'::vector ASC
            LIMIT :limit
        ) ranked
        INNER JOIN chunk c ON c.id = ranked.chunk_id AND c.status = 'processed'
        INNER JOIN source s ON s.id = c.source_id
        {exclude_join_condition}
    """
    
    return sql_query, params


def _execute_vector_search_query(
    sql_query: str,
    params: Dict[str, Any],
    top_k: int,
    db: Session,
    include_source_id: bool = False
) -> List[Dict[str, Any]]:
    """Thực thi vector search SQL query và trả về kết quả đã được format.
    
    Hàm này thực thi SQL query với parameters, format kết quả thành dictionary
    structure chuẩn, và giới hạn số lượng kết quả về top_k.
    
    Args:
        sql_query: SQL query string cần thực thi
        params: Dictionary chứa parameters cho query
        top_k: Số lượng kết quả tối đa cần trả về
        db: Database session
        include_source_id: Có bao gồm source_id trong kết quả không
    
    Returns:
        List[Dict[str, Any]]: Danh sách các chunks đã được format, mỗi chunk chứa:
            - text: Nội dung text của chunk
            - metadata: Dictionary chứa metadata (source_reference, source_type, etc.)
            - similarity_score: Điểm similarity (float)
            - chunk_id: ID của chunk
            - source_id: ID của source (nếu include_source_id=True)
    
    Raises:
        Exception: Nếu SQL query thất bại (sẽ được log và re-raise)
    
    Note:
        - Kết quả được format bằng format_search_results()
        - Chỉ trả về top_k kết quả đầu tiên
    """
    try:
        result = db.execute(text(sql_query), params)
        rows = result.fetchall()
    except Exception as query_error:
        logger.error(f"Vector search query failed: {query_error}", exc_info=True)
        raise
    
    # Định dạng kết quả
    results = format_search_results(rows, include_source_id=include_source_id)
    
    # Giới hạn top_k kết quả
    return results[:top_k]


def _search_with_fallback_threshold(
    sql_query: str,
    params: Dict[str, Any],
    similarity_threshold: float,
    top_k: int,
    db: Session,
    include_source_id: bool = False
) -> List[Dict[str, Any]]:
    """Thử lại tìm kiếm với threshold thấp hơn nếu không tìm thấy kết quả.
    
    Hàm này thực hiện fallback strategy khi không tìm thấy kết quả với threshold
    ban đầu. Sẽ thử lại với các threshold thấp hơn (0.3, 0.2, 0.1, 0.05) cho đến
    khi tìm thấy kết quả hoặc hết các threshold.
    
    Quy trình:
    1. Lặp qua các threshold thấp hơn trong LOWER_THRESHOLDS
    2. Chỉ thử threshold thấp hơn threshold ban đầu
    3. Thực thi query với threshold mới
    4. Trả về kết quả ngay khi tìm thấy
    
    Args:
        sql_query: SQL query string (đã được build sẵn)
        params: Dictionary parameters cho query (sẽ được update với threshold mới)
        similarity_threshold: Threshold ban đầu (float)
        top_k: Số lượng kết quả tối đa cần trả về
        db: Database session
        include_source_id: Có bao gồm source_id trong kết quả không
    
    Returns:
        List[Dict[str, Any]]: Danh sách chunks nếu tìm thấy, list rỗng nếu không
    
    Note:
        - Chỉ thử các threshold thấp hơn threshold ban đầu
        - Trả về ngay khi tìm thấy kết quả đầu tiên
        - Nếu không tìm thấy với bất kỳ threshold nào, trả về list rỗng
    """
    for lower_threshold in LOWER_THRESHOLDS:
        if similarity_threshold > lower_threshold:
            logger.info(f"Retrying with lower threshold: {lower_threshold}")
            params['threshold'] = lower_threshold
            result = db.execute(text(sql_query), params)
            rows = result.fetchall()
            results = format_search_results(rows[:top_k], include_source_id=include_source_id)
            if results:
                return results
    
    return []

