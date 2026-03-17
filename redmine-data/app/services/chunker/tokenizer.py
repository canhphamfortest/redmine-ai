"""Các tiện ích tokenizer cho chunking.

Module này cung cấp Tokenizer class để đếm tokens trong văn bản:
- Tokenizer: Class sử dụng tiktoken để đếm tokens chính xác
- Fallback mechanism: Ước tính token count nếu encoding không khả dụng

Sử dụng tiktoken encoding "cl100k_base" tương thích với GPT-4 và các model mới.
"""
import logging
import tiktoken

logger = logging.getLogger(__name__)


class Tokenizer:
    """Tiện ích đếm token sử dụng tiktoken encoding.
    
    Class này cung cấp chức năng đếm token cho văn bản sử dụng tiktoken,
    thư viện encoding chính thức của OpenAI. Hỗ trợ fallback nếu không
    thể load encoding.
    
    Attributes:
        encoding: Tiktoken encoding object (có thể None nếu load thất bại)
    """
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """Khởi tạo Tokenizer với encoding name.
        
        Args:
            encoding_name: Tên encoding để sử dụng (mặc định: "cl100k_base").
                Encoding này tương thích với GPT-4 và các model mới của OpenAI.
        
        Note:
            Nếu không thể load encoding, self.encoding sẽ là None và sẽ sử dụng
            fallback estimation khi đếm token.
        """
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to load tokenizer {encoding_name}: {e}")
            self.encoding = None
    
    def token_length(self, text: str) -> int:
        """Đếm số lượng token trong văn bản.
        
        Hàm này encode văn bản thành tokens và trả về số lượng. Nếu encoding
        không khả dụng, sẽ sử dụng ước tính thô (chia độ dài cho 4).
        
        Args:
            text: Văn bản cần đếm token (string)
        
        Returns:
            int: Số lượng token trong văn bản
        
        Example:
            >>> tokenizer = Tokenizer()
            >>> tokenizer.token_length("Hello world")
            2
            >>> # Nếu encoding không khả dụng, sẽ ước tính
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback: ước tính thô (trung bình 1 token = 4 ký tự)
            return len(text) // 4

