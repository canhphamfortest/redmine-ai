"""Content builder cho Redmine issues và wiki pages.

Module này cung cấp ContentBuilder class để xây dựng searchable content:
- build_issue_content: Xây dựng content từ Redmine issue (description, comments, attachments)
- build_wiki_content: Xây dựng content từ Redmine wiki page

Content được xây dựng từ tất cả text-based data trong issue/wiki để tối đa hóa
khả năng tìm kiếm. Bao gồm description, journal entries, và text attachments.
"""
import logging
from redminelib import Redmine

from app.services.redmine.utils import safe_attr, is_text_file, download_attachment_content, sanitize_string

logger = logging.getLogger(__name__)


class ContentBuilder:
    """Xây dựng chuỗi content có thể tìm kiếm từ các đối tượng Redmine.
    
    Class này chuyển đổi Redmine objects (issues, wiki pages) thành text
    content có thể được chunk và embed. Bao gồm metadata, description,
    comments, và nội dung text attachments.
    
    Attributes:
        redmine: Redmine client instance để download attachments
    """
    
    def __init__(self, redmine: Redmine):
        """Khởi tạo ContentBuilder.
        
        Args:
            redmine: Redmine client instance
        """
        self.redmine = redmine
    
    def build_issue_content(self, issue) -> str:
        """Xây dựng content text có thể tìm kiếm từ Redmine issue.
        
        Hàm này tổng hợp tất cả thông tin từ issue thành một chuỗi text:
        - Issue ID và subject
        - Metadata (tracker, status, priority, author)
        - Description
        - Comments (journals)
        - Nội dung text attachments
        
        Args:
            issue: Redmine issue object từ redminelib
        
        Returns:
            str: Chuỗi text chứa tất cả thông tin issue, các phần được
                nối bằng newline. Format:
                - "Issue #ID: Subject"
                - Metadata lines
                - "Description:" + description
                - "Comments:" + comments
                - "Attachment: filename" + content (cho text files)
        
        Note:
            - Chỉ bao gồm text attachments (được xác định bằng is_text_file())
            - Attachments được download bằng download_attachment_content()
            - Nếu download attachment thất bại, sẽ skip và log debug
            - Comments chỉ lấy những có notes
        """
        # Sanitize subject và description để loại bỏ null bytes
        subject = sanitize_string(issue.subject if hasattr(issue, 'subject') else '')
        description = sanitize_string(issue.description or '' if hasattr(issue, 'description') else '')
        
        parts = [
            f"Issue #{issue.id}: {subject}",
            "",
            f"Tracker: {sanitize_string(issue.tracker.name if hasattr(issue, 'tracker') and hasattr(issue.tracker, 'name') else 'N/A')}",
            f"Status: {sanitize_string(issue.status.name if hasattr(issue, 'status') and hasattr(issue.status, 'name') else 'N/A')}",
            f"Priority: {sanitize_string(issue.priority.name if hasattr(issue, 'priority') and hasattr(issue.priority, 'name') else 'N/A')}",
            f"Author: {sanitize_string(issue.author.name if hasattr(issue, 'author') and hasattr(issue.author, 'name') else 'N/A')}",
            "",
            "Description:",
            description,
        ]
        
        # Thêm comments
        if hasattr(issue, 'journals'):
            parts.append("")
            parts.append("Comments:")
            for journal in issue.journals:
                if hasattr(journal, 'notes') and journal.notes:
                    author = sanitize_string(journal.user.name if hasattr(journal, 'user') and hasattr(journal.user, 'name') else 'Unknown')
                    notes = sanitize_string(journal.notes)
                    parts.append(f"\n[{author}]: {notes}")
        
        # Thêm nội dung các file text attachments
        if hasattr(issue, 'attachments'):
            for attachment in issue.attachments:
                filename = safe_attr(attachment, 'filename')
                content_type = safe_attr(attachment, 'content_type')
                attachment_id = safe_attr(attachment, 'id')
                
                if attachment_id and is_text_file(filename, content_type):
                    try:
                        content = download_attachment_content(self.redmine, attachment_id)
                        if content:
                            # Content đã được sanitize trong download_attachment_content
                            parts.append("")
                            parts.append(f"Attachment: {sanitize_string(filename)}")
                            parts.append(content)
                    except Exception as e:
                        logger.debug(f"Could not include attachment {attachment_id} in content hash: {e}")
        
        return "\n".join(parts)
    
    def build_wiki_content(self, wiki_page) -> str:
        """Xây dựng content text có thể tìm kiếm từ Redmine wiki page.
        
        Hàm này extract text content từ wiki page. Wiki pages thường đơn giản
        hơn issues, chỉ cần title và text content.
        
        Args:
            wiki_page: Redmine wiki page object từ redminelib
        
        Returns:
            str: Chuỗi text chứa:
                - "Wiki Page: {title}"
                - Text content của wiki page
        
        Note:
            - Format đơn giản: title + text content
            - Không bao gồm metadata phức tạp như issues
            - Text được lấy từ wiki_page.text attribute
        """
        # Sanitize title và text để loại bỏ null bytes
        title = sanitize_string(wiki_page.title if hasattr(wiki_page, 'title') else '')
        text = sanitize_string(wiki_page.text if hasattr(wiki_page, 'text') and wiki_page.text else '')
        
        parts = [
            f"Wiki Page: {title}",
            "",
        ]
        
        if text:
            parts.append(text)
        
        return "\n".join(parts)

