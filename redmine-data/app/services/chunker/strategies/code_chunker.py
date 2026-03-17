"""Chiến lược chunking code.

Module này cung cấp function để chia source code thành chunks:
- chunk_code: Chia code với preserve cấu trúc functions/classes

Sử dụng language-specific splitters từ langchain để giữ functions và classes
cùng nhau. Hỗ trợ nhiều ngôn ngữ lập trình phổ biến.
"""
import logging
from typing import List, Dict, Any
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter

from app.services.chunker.tokenizer import Tokenizer
from app.services.chunker.strategies.text_chunker import chunk_text

logger = logging.getLogger(__name__)


def chunk_code(
    code: str,
    tokenizer: Tokenizer,
    chunk_size: int,
    chunk_overlap: int,
    language: str = "python",
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Chia code thành các chunk với bảo toàn cấu trúc function/class.
    
    Hàm này sử dụng language-specific splitter từ langchain để chia code
    trong khi cố gắng giữ nguyên cấu trúc (functions, classes cùng nhau).
    Hỗ trợ nhiều ngôn ngữ lập trình phổ biến.
    
    Quy trình:
    1. Ánh xạ tên ngôn ngữ sang Language enum của langchain
    2. Sử dụng RecursiveCharacterTextSplitter.from_language nếu ngôn ngữ được hỗ trợ
    3. Fallback về text splitter thông thường nếu ngôn ngữ không được hỗ trợ
    4. Nếu có lỗi, fallback về chunk_text() thông thường
    
    Args:
        code: Source code cần chia (string)
        tokenizer: Tokenizer instance để đếm token
        chunk_size: Kích thước tối đa của mỗi chunk (tính bằng token)
        chunk_overlap: Số token chồng chéo giữa các chunk liên tiếp
        language: Tên ngôn ngữ lập trình (mặc định: "python").
            Hỗ trợ: python, javascript, java, cpp, go, rust, markdown
        metadata: Dictionary metadata tùy chọn để thêm vào mỗi chunk
    
    Returns:
        List[Dict[str, Any]]: Danh sách các chunk, mỗi chunk là dictionary chứa:
            - ordinal: Thứ tự chunk (int)
            - text_content: Nội dung code của chunk (str)
            - token_count: Số lượng token trong chunk (int)
            - chunk_type: "code" (str)
            - code_language: Ngôn ngữ lập trình (str)
            - Các fields từ metadata nếu có
    
    Note:
        - Nếu ngôn ngữ không được hỗ trợ, sẽ sử dụng text splitter thông thường
        - Nếu có exception, sẽ fallback về chunk_text() với chunk_type='code'
    """
    # Đối với code, chúng ta muốn giữ functions/classes cùng nhau
    try:
        # Ánh xạ tên ngôn ngữ
        lang_map = {
            'python': Language.PYTHON,
            'javascript': Language.JS,
            'java': Language.JAVA,
            'cpp': Language.CPP,
            'go': Language.GO,
            'rust': Language.RUST,
            'markdown': Language.MARKDOWN,
        }
        
        lang_enum = lang_map.get(language.lower())
        
        if lang_enum:
            code_splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang_enum,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        else:
            # Fallback về splitter thông thường
            code_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=tokenizer.token_length,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
        
        text_chunks = code_splitter.split_text(code)
        
        # Tạo các đối tượng chunk
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                'ordinal': i,
                'text_content': chunk_text,
                'token_count': tokenizer.token_length(chunk_text),
                'chunk_type': 'code',
                'code_language': language,
            }
            
            if metadata:
                chunk.update(metadata)
            
            chunks.append(chunk)
        
        return chunks
        
    except Exception as e:
        logger.error(f"Code chunking failed: {e}")
        # Fallback về chunking thông thường
        return chunk_text(code, tokenizer, chunk_size, chunk_overlap, metadata, chunk_type='code')

