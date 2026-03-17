"""Lớp chunker văn bản chính"""
import logging
from typing import List, Dict, Any

from app.config import settings
from app.services.chunker.tokenizer import Tokenizer
from app.services.chunker.strategies import (
    chunk_text,
    chunk_code,
    chunk_redmine_issue,
    chunk_redmine_wiki
)

logger = logging.getLogger(__name__)


class TextChunker:
    """Chia văn bản thành các chunk để embedding và tìm kiếm.
    
    Class này cung cấp các phương thức để chia văn bản, code, và Redmine data
    thành các chunks nhỏ hơn. Mỗi chunk có kích thước giới hạn (tính bằng tokens)
    để phù hợp với embedding models và tìm kiếm hiệu quả.
    
    Attributes:
        chunk_size: Kích thước tối đa của mỗi chunk (tính bằng tokens) (int)
        chunk_overlap: Số lượng tokens chồng lấn giữa các chunk liên tiếp (int)
        tokenizer: Tokenizer instance để đếm tokens (Tokenizer)
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        encoding_name: str = "cl100k_base"
    ):
        """Khởi tạo TextChunker.
        
        Args:
            chunk_size: Kích thước chunk. Nếu None, sử dụng settings.chunk_size
            chunk_overlap: Độ chồng lấn. Nếu None, sử dụng settings.chunk_overlap
            encoding_name: Tên encoding cho tokenizer (mặc định: "cl100k_base")
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.tokenizer = Tokenizer(encoding_name)
    
    def _token_length(self, text: str) -> int:
        """Đếm số token trong văn bản.
        
        Args:
            text: Văn bản cần đếm token (string)
        
        Returns:
            int: Số lượng tokens trong văn bản
        """
        return self.tokenizer.token_length(text)
    
    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        chunk_type: str = "text"
    ) -> List[Dict[str, Any]]:
        """Chia văn bản thành các chunk nhỏ hơn.
        
        Hàm này sử dụng RecursiveCharacterTextSplitter để chia văn bản thành
        các chunks với kích thước và overlap được cấu hình.
        
        Args:
            text: Văn bản cần chia (string)
            metadata: Metadata bổ sung để thêm vào mỗi chunk (dict, optional)
            chunk_type: Loại chunk ("text", "code", etc.) (string, mặc định: "text")
        
        Returns:
            List[Dict[str, Any]]: Danh sách các chunk, mỗi chunk chứa:
                - text_content: Nội dung văn bản của chunk (str)
                - token_count: Số lượng tokens trong chunk (int)
                - chunk_type: Loại chunk (str)
                - metadata: Metadata của chunk (dict)
                - ordinal: Thứ tự của chunk (int, 0-based)
        
        Note:
            - Sử dụng RecursiveCharacterTextSplitter với các separators thông minh
            - Chunks được đánh số ordinal để giữ thứ tự
            - Metadata được merge với metadata mặc định của chunk
        """
        return chunk_text(
            text,
            self.tokenizer,
            self.chunk_size,
            self.chunk_overlap,
            metadata,
            chunk_type
        )
    
    def chunk_code(
        self,
        code: str,
        language: str = "python",
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Chia code thành chunks với bối cảnh function/class được giữ lại.
        
        Hàm này sử dụng language-specific text splitter để chia code thành
        chunks, cố gắng bảo toàn ngữ cảnh của functions và classes.
        
        Args:
            code: Chuỗi code cần chia (string)
            language: Ngôn ngữ lập trình (python, java, javascript, etc.) (string, mặc định: "python")
            metadata: Metadata bổ sung để thêm vào mỗi chunk (dict, optional)
        
        Returns:
            List[Dict[str, Any]]: Danh sách các chunk code, mỗi chunk chứa:
                - text_content: Nội dung code của chunk (str)
                - token_count: Số lượng tokens trong chunk (int)
                - chunk_type: "code" (str)
                - metadata: Metadata của chunk, bao gồm language (dict)
                - ordinal: Thứ tự của chunk (int, 0-based)
        
        Note:
            - Sử dụng RecursiveCharacterTextSplitter.from_language() nếu ngôn ngữ được hỗ trợ
            - Fallback về RecursiveCharacterTextSplitter thông thường nếu không hỗ trợ
            - Language được thêm vào metadata của mỗi chunk
        """
        return chunk_code(
            code,
            self.tokenizer,
            self.chunk_size,
            self.chunk_overlap,
            language,
            metadata
        )
    
    def chunk_redmine_issue(
        self,
        issue_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chia Redmine issue thành chunks với xử lý đặc biệt.
        
        Hàm này xử lý đặc biệt cho Redmine issue data:
        - Tạo một chunk metadata riêng chứa thông tin quan trọng (ID, title, status, etc.)
        - Chia description thành chunks
        - Chia journals (comments) thành chunks
        - Chia attachments content thành chunks
        
        Args:
            issue_data: Dictionary chứa dữ liệu Redmine issue (dict):
                - id: Issue ID (int)
                - title: Subject của issue (str)
                - description: Mô tả issue (str)
                - journals: Danh sách comments (List[Dict])
                - attachments: Danh sách attachments với content (List[Dict])
                - Các metadata khác (tracker, status, priority, etc.)
        
        Returns:
            List[Dict[str, Any]]: Danh sách các chunk từ issue, mỗi chunk chứa:
                - text_content: Nội dung văn bản của chunk (str)
                - token_count: Số lượng tokens trong chunk (int)
                - chunk_type: Loại chunk ("issue_metadata", "description", "journal", "attachment") (str)
                - metadata: Metadata của chunk, bao gồm issue info (dict)
                - ordinal: Thứ tự của chunk (int, 0-based)
        
        Note:
            - Chunk metadata được đặt đầu tiên để tăng khả năng tìm kiếm
            - Mỗi journal và attachment được chunk riêng
            - Metadata chunk chứa đầy đủ thông tin issue để tìm kiếm nhanh
        """
        return chunk_redmine_issue(
            issue_data,
            self.tokenizer,
            self.chunk_size,
            self.chunk_overlap
        )
    
    def chunk_redmine_wiki(
        self,
        wiki_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chia Redmine wiki page thành chunks với xử lý đặc biệt cho metadata.
        
        Hàm này xử lý đặc biệt cho Redmine wiki page data:
        - Tạo một chunk metadata riêng chứa thông tin quan trọng (title, author, project, etc.)
        - Chia text content thành chunks
        
        Args:
            wiki_data: Dictionary chứa dữ liệu Redmine wiki page (dict):
                - title: Tiêu đề wiki page (str)
                - text: Nội dung wiki page (str)
                - version: Phiên bản wiki page (int, optional)
                - author: Thông tin tác giả (dict, optional)
                - project: Thông tin project (dict, optional)
                - Các metadata khác (created_on, updated_on, comments, etc.)
        
        Returns:
            List[Dict[str, Any]]: Danh sách các chunk từ wiki page, mỗi chunk chứa:
                - text_content: Nội dung văn bản của chunk (str)
                - token_count: Số lượng tokens trong chunk (int)
                - chunk_type: Loại chunk ("wiki_metadata", "wiki_content") (str)
                - metadata: Metadata của chunk, bao gồm wiki info (dict)
                - ordinal: Thứ tự của chunk (int, 0-based)
        
        Note:
            - Chunk metadata được đặt đầu tiên để tăng khả năng tìm kiếm
            - Text content được chia thành các chunks với overlap
            - Metadata chunk chứa đầy đủ thông tin wiki để tìm kiếm nhanh
        """
        return chunk_redmine_wiki(
            wiki_data,
            self.tokenizer,
            self.chunk_size,
            self.chunk_overlap
        )

