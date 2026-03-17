"""Handler attachment cho Redmine issues.

Module này cung cấp AttachmentHandler class để xử lý attachments:
- Attachment processing: Extract metadata và download content từ attachments
- Text file detection: Phát hiện text files để download content
- Content download: Download text content từ Redmine API
- Content truncation: Cắt bớt content nếu quá dài để tránh overload server

Chỉ download content cho text files để tránh tốn tài nguyên với binary files.
"""
import logging
from typing import Dict, Any, List
from redminelib import Redmine

from app.services.redmine.utils import safe_attr, is_text_file, download_attachment_content, sanitize_string
from app.config import settings

logger = logging.getLogger(__name__)


class AttachmentHandler:
    """Xử lý attachments cho Redmine issues.
    
    Class này xử lý việc extract metadata và download content của attachments
    từ Redmine issues. Chỉ download content cho text files để tránh tốn
    tài nguyên với binary files.
    
    Attributes:
        redmine: Redmine client instance để download attachments
    """
    
    def __init__(self, redmine: Redmine):
        """Khởi tạo AttachmentHandler.
        
        Args:
            redmine: Redmine client instance
        """
        self.redmine = redmine
    
    def process_attachments(self, issue) -> List[Dict[str, Any]]:
        """Xử lý tất cả attachments từ issue và tải nội dung text files.
        
        Hàm này duyệt qua tất cả attachments của issue, extract metadata,
        và download content cho các text files. Binary files chỉ có metadata.
        
        Args:
            issue: Redmine issue object có attachments attribute
        
        Returns:
            List[Dict[str, Any]]: Danh sách dictionaries, mỗi dict chứa:
                - id: Attachment ID (int)
                - filename: Tên file (str)
                - filesize: Kích thước file (int)
                - content_type: MIME type (str)
                - description: Mô tả attachment (str, optional)
                - author: Dictionary với id, name (dict)
                - created_on: Thời gian tạo (str, ISO format)
                - content: Nội dung text (str, chỉ có cho text files)
        
        Note:
            - Chỉ download content cho text files (xác định bằng is_text_file())
            - Content được download bằng download_attachment_content()
            - Nếu download thất bại, attachment vẫn có trong list nhưng không có content
            - Lỗi download được log nhưng không làm gián đoạn quá trình
        """
        attachments_data = []
        
        if not hasattr(issue, 'attachments'):
            return attachments_data
        
        for attachment in issue.attachments:
            attachment_author = attachment.author if hasattr(attachment, 'author') else None
            filename = safe_attr(attachment, 'filename')
            content_type = safe_attr(attachment, 'content_type')
            attachment_id = safe_attr(attachment, 'id')
            
            attachment_data = {
                'id': attachment_id,
                'filename': sanitize_string(filename),
                'filesize': safe_attr(attachment, 'filesize'),
                'content_type': sanitize_string(content_type),
                'description': sanitize_string(safe_attr(attachment, 'description')),
                'author': {
                    'id': safe_attr(attachment_author, 'id'),
                    'name': sanitize_string(safe_attr(attachment_author, 'name'))
                },
                'created_on': attachment.created_on.isoformat() if hasattr(attachment, 'created_on') and attachment.created_on else None
            }
            
            # Tải nội dung cho các file text
            if attachment_id and is_text_file(filename, content_type):
                try:
                    content = download_attachment_content(self.redmine, attachment_id)
                    if content:
                        original_size = len(content)
                        max_size = settings.max_attachment_content_size
                        
                        # Tất cả file đều lấy 2500 chars từ đầu và 2500 chars từ cuối (tổng 5000 chars)
                        # để có context và thông tin mới nhất, tránh overload server
                        if original_size > max_size:
                            # Lấy phần đầu và phần cuối, mỗi phần = max_size / 2
                            half_size = max_size // 2
                            header = content[:half_size]
                            footer = content[-half_size:]
                            
                            content = f"{header}\n\n... [truncated {original_size - max_size} chars] ...\n\n{footer}"
                            
                            logger.warning(
                                f"Truncated attachment {attachment_id} content: {filename} "
                                f"({original_size} -> {len(content)} chars, limit: {max_size}). "
                                f"Content truncated to avoid processing large files."
                            )
                        else:
                            logger.info(
                                f"Downloaded content for text attachment {attachment_id}: "
                                f"{filename} ({original_size} chars)"
                            )
                        
                        # Content đã được sanitize trong download_attachment_content
                        attachment_data['content'] = content
                    else:
                        logger.warning(f"Could not download content for attachment {attachment_id}: {filename}")
                except Exception as e:
                    logger.error(f"Error downloading attachment {attachment_id} content: {e}", exc_info=True)
            
            attachments_data.append(attachment_data)
        
        return attachments_data

