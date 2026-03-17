"""Xây dựng context và prompt cho RAG chain.

Module này cung cấp các functions để xây dựng context và prompt cho RAG pipeline:
- build_context: Format các chunks thành context string có cấu trúc
- create_prompt: Tạo prompt hoàn chỉnh với system instructions, context, và query

Context được xây dựng với ưu tiên cho issue_metadata chunks để LLM có thể
hiểu rõ hơn về các issues liên quan trước khi đọc chi tiết.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def build_context(chunks: List[Dict[str, Any]]) -> str:
    """Xây dựng chuỗi context từ các chunks đã retrieve để đưa vào prompt.
    
    Hàm này format các chunks thành một chuỗi context có cấu trúc để LLM
    có thể hiểu và sử dụng. Đặc biệt ưu tiên các chunks issue_metadata
    (metadata của Redmine issues) bằng cách đặt chúng lên đầu và đánh dấu
    rõ ràng.
    
    Quy trình:
    1. Tách chunks thành issue_metadata và các chunks khác
    2. Sắp xếp issue_metadata theo similarity score (nếu có)
    3. Kết hợp: issue_metadata trước, sau đó các chunks khác
    4. Format mỗi chunk với source label và nội dung
    
    Args:
        chunks: Danh sách chunks đã được retrieve, mỗi chunk chứa:
            - text: Nội dung text của chunk
            - chunk_type: Loại chunk (issue_metadata, issue_description, etc.)
            - metadata: Dictionary chứa source_reference, source_type, heading, etc.
            - similarity_score hoặc rrf_score: Điểm relevance (optional)
    
    Returns:
        str: Chuỗi context đã được format, mỗi chunk được đánh số và có
            source label. Trả về "Không tìm thấy thông tin liên quan." nếu
            chunks rỗng.
    
    Note:
        - Issue metadata chunks được đánh dấu với [ISSUE METADATA]
        - Mỗi chunk được đánh số [Source 1], [Source 2], etc.
        - Source label lấy từ source_reference, heading, hoặc 'Unknown'
        - Chunks được nối bằng newline
    """
    if not chunks:
        return "Không tìm thấy thông tin liên quan."
    
    # Tách các chunks issue_metadata khỏi các chunks khác
    issue_metadata_chunks = []
    other_chunks = []
    
    for chunk in chunks:
        if chunk.get('chunk_type') == 'issue_metadata':
            issue_metadata_chunks.append(chunk)
        else:
            other_chunks.append(chunk)
    
    # Sắp xếp các chunks issue_metadata theo điểm số (nếu có)
    if issue_metadata_chunks:
        issue_metadata_chunks.sort(
            key=lambda x: x.get('similarity_score', x.get('rrf_score', 0.0)),
            reverse=True
        )
    
    # Kết hợp: issue_metadata trước, sau đó các chunks khác
    sorted_chunks = issue_metadata_chunks + other_chunks
    
    context_parts = []
    
    for i, chunk in enumerate(sorted_chunks, 1):
        metadata = chunk.get('metadata', {})
        chunk_type = chunk.get('chunk_type', '')
        
        # Xây dựng source label
        source_label = metadata.get('source_reference') or metadata.get('heading') or 'Unknown'
        source_info = f"[Source {i}] {source_label}"
        
        if metadata.get('source_type'):
            source_info += f" ({metadata['source_type']})"
        
        # Thêm chỉ báo chunk type cho issue_metadata
        if chunk_type == 'issue_metadata':
            source_info += " [ISSUE METADATA]"
        
        # Định dạng issue_metadata đặc biệt để dễ đọc hơn
        chunk_text = chunk['text']
        if chunk_type == 'issue_metadata':
            # Issue metadata đã được định dạng tốt, chỉ cần thêm header
            context_parts.append(f"{source_info}\n{chunk_text}\n")
        else:
            context_parts.append(f"{source_info}\n{chunk_text}\n")
    
    return "\n".join(context_parts)


def create_prompt(query: str, context: str) -> str:
    """Tạo prompt hoàn chỉnh cho LLM với context và hướng dẫn.
    
    Hàm này tạo prompt theo format chuẩn cho RAG (Retrieval-Augmented Generation),
    bao gồm:
    - System instructions: Vai trò và quy tắc của AI assistant
    - Context: Thông tin đã retrieve từ knowledge base
    - User query: Câu hỏi của người dùng
    
    Prompt được thiết kế để:
    - Yêu cầu LLM chỉ sử dụng thông tin từ context
    - Khuyến khích trích dẫn nguồn
    - Ngăn chặn việc bịa đáp án khi không có thông tin
    
    Args:
        query: Câu hỏi của người dùng (string)
        context: Chuỗi context đã được build từ chunks (string)
    
    Returns:
        str: Prompt hoàn chỉnh để gửi đến LLM
    
    Note:
        - Prompt được viết bằng tiếng Việt
        - Context được chèn trực tiếp vào prompt
        - Prompt yêu cầu LLM trích dẫn nguồn khi có thể
    """
    prompt = f"""Bạn là một AI assistant chuyên trợ giúp trả lời câu hỏi dựa trên Redmine Issues và Wiki Pages.

Quy tắc:
1. CHỈ sử dụng thông tin từ context được cung cấp
2. Bạn đã tìm thấy các issues và wiki pages liên quan đến câu hỏi của người dùng, hãy tổng hợp lại kết quả trả lời câu hỏi của người dùng
3. Trích dẫn nguồn khi có thể (vd: "Theo Issue #976 hoặc Source...")
4. Ngắn gọn, rõ ràng, chính xác
5. KHÔNG bịa đáp án nếu không có thông tin trong context

Context:
{context}

Câu hỏi: {query}

Trả lời:"""
    
    return prompt

