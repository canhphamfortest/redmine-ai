"""Chiến lược chunking văn bản.

Module này cung cấp function để chia văn bản thông thường thành chunks:
- chunk_text: Chia văn bản với overlap và preserve cấu trúc

Sử dụng RecursiveCharacterTextSplitter từ langchain để chia văn bản
một cách thông minh, ưu tiên tách tại các điểm ngắt tự nhiên.
"""
import logging
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.services.chunker.tokenizer import Tokenizer

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    tokenizer: Tokenizer,
    chunk_size: int,
    chunk_overlap: int,
    metadata: Dict[str, Any] = None,
    chunk_type: str = "text"
) -> List[Dict[str, Any]]:
    """Chia văn bản thành các chunk với kích thước và overlap được chỉ định.
    
    Hàm này sử dụng RecursiveCharacterTextSplitter từ langchain để chia văn bản
    thành các chunk. Splitter sẽ cố gắng giữ nguyên cấu trúc văn bản bằng cách
    ưu tiên tách tại các điểm ngắt tự nhiên (paragraph, sentence, word).
    
    Quy trình:
    1. Sử dụng RecursiveCharacterTextSplitter với separators ưu tiên
    2. Đo độ dài bằng token thay vì ký tự
    3. Tạo các chunk objects với metadata đầy đủ
    
    Args:
        text: Văn bản cần chia (string)
        tokenizer: Tokenizer instance để đếm token
        chunk_size: Kích thước tối đa của mỗi chunk (tính bằng token)
        chunk_overlap: Số token chồng chéo giữa các chunk liên tiếp
        metadata: Dictionary metadata tùy chọn để thêm vào mỗi chunk
        chunk_type: Loại chunk (mặc định: "text")
    
    Returns:
        List[Dict[str, Any]]: Danh sách các chunk, mỗi chunk là dictionary chứa:
            - ordinal: Thứ tự chunk (int)
            - text_content: Nội dung text của chunk (str)
            - token_count: Số lượng token trong chunk (int)
            - chunk_type: Loại chunk (str)
            - Các fields từ metadata nếu có
    
    Note:
        - Trả về list rỗng nếu text rỗng hoặc None
        - Trả về list rỗng nếu có lỗi trong quá trình chunking
        - Separators được ưu tiên: paragraph breaks, line breaks, sentences, words
    """
    if not text or not text.strip():
        return []
    
    try:
        # Khởi tạo text splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=tokenizer.token_length,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Chia văn bản
        text_chunks = splitter.split_text(text)
        
        # Tạo các đối tượng chunk
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                'ordinal': i,
                'text_content': chunk_text,
                'token_count': tokenizer.token_length(chunk_text),
                'chunk_type': chunk_type,
            }
            
            # Thêm metadata nếu được cung cấp
            if metadata:
                chunk.update(metadata)
            
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from text of length {len(text)}")
        return chunks
        
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        return []

