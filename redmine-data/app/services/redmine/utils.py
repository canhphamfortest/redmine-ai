"""Các hàm utility cho Redmine sync.

Module này cung cấp các helper functions cho Redmine synchronization:
- safe_attr: Safely get attributes từ Redmine objects
- is_transaction_aborted_error: Kiểm tra database transaction errors
- is_text_file: Phát hiện text files dựa trên MIME type
- download_attachment_content: Download text content từ Redmine attachments

Các functions này giúp xử lý Redmine API responses một cách an toàn và hiệu quả.
"""
import logging
import os
import requests
from typing import Optional
from redminelib import Redmine

from app.config import settings

logger = logging.getLogger(__name__)


def safe_attr(obj, attr, default=None):
    """Lấy attribute từ object một cách an toàn, tránh lỗi AttributeError.
    
    Hàm này kiểm tra object có None không và xử lý exception khi attribute
    không tồn tại. Hữu ích khi làm việc với Redmine objects có thể thiếu
    một số attributes tùy chọn.
    
    Args:
        obj: Object cần lấy attribute (có thể là None)
        attr: Tên attribute cần lấy (string)
        default: Giá trị mặc định trả về nếu object None hoặc attribute không tồn tại
    
    Returns:
        Giá trị của attribute nếu tồn tại, hoặc default nếu không
    
    Example:
        >>> issue = redmine.issue.get(123)
        >>> status = safe_attr(issue, 'status', 'unknown')
        >>> # Không bị lỗi nếu issue.status không tồn tại
    """
    if obj is None:
        return default
    try:
        return getattr(obj, attr)
    except AttributeError:
        return default


def is_transaction_aborted_error(e: Exception) -> bool:
    """Kiểm tra xem exception có phải do database transaction bị abort không.
    
    Hàm này phân tích message của exception để xác định xem có phải là lỗi
    transaction abort hay không. Hữu ích để xử lý lỗi database một cách
    thông minh, đặc biệt trong các trường hợp retry logic.
    
    Args:
        e: Exception object cần kiểm tra
    
    Returns:
        bool: True nếu exception có vẻ là transaction abort error, False nếu không
    
    Example:
        >>> try:
        ...     db.commit()
        ... except Exception as e:
        ...     if is_transaction_aborted_error(e):
        ...         # Xử lý đặc biệt cho transaction abort
        ...         db.rollback()
    """
    error_str = str(e).lower()
    return 'transaction' in error_str and ('aborted' in error_str or 'failed' in error_str)


def is_text_file(filename: str, content_type: str = None) -> bool:
    """Kiểm tra xem file có phải là text file dựa trên extension và content type.
    
    Hàm này xác định file có thể được đọc như text file không bằng cách:
    1. Kiểm tra extension của file (nếu có)
    2. Kiểm tra MIME content type (nếu được cung cấp)
    
    Hàm hỗ trợ nhiều loại text files bao gồm: plain text, markdown, code files,
    config files, và các định dạng text-based khác.
    
    Args:
        filename: Tên file hoặc đường dẫn file (có thể là None)
        content_type: MIME content type của file (tùy chọn)
    
    Returns:
        bool: True nếu file được xác định là text file, False nếu không
    
    Example:
        >>> is_text_file("document.txt")
        True
        >>> is_text_file("image.png")
        False
        >>> is_text_file("script.py", "text/x-python")
        True
    """
    if not filename:
        return False
    
    # Các extension file text
    text_extensions = {'.txt', '.md', '.markdown', '.rst', '.log', '.csv', 
                      '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg', 
                      '.conf', '.properties', '.env', '.sh', '.bat', '.ps1',
                      '.sql', '.py', '.js', '.ts', '.html', '.css', '.scss',
                      '.java', '.cpp', '.c', '.h', '.hpp', '.go', '.rs', '.rb',
                      '.php', '.swift', '.kt', '.dart', '.vue', '.jsx', '.tsx'}
    
    # Lấy file extension
    _, ext = os.path.splitext(filename.lower())
    if ext in text_extensions:
        return True
    
    # Kiểm tra content type nếu được cung cấp
    if content_type:
        text_content_types = {
            'text/plain', 'text/markdown', 'text/x-markdown',
            'text/csv', 'application/json', 'application/xml',
            'text/xml', 'text/yaml', 'text/x-yaml',
            'text/html', 'text/css', 'text/javascript',
            'application/javascript', 'application/x-javascript'
        }
        if content_type.lower() in text_content_types:
            return True
    
    return False


def sanitize_string(s: Optional[str]) -> Optional[str]:
    """Loại bỏ null bytes (0x00) khỏi string để tránh lỗi database.
    
    PostgreSQL và SQLAlchemy không cho phép null bytes trong string literals.
    Hàm này loại bỏ tất cả null bytes khỏi string trước khi lưu vào database.
    
    Args:
        s: String cần sanitize (có thể là None)
    
    Returns:
        str | None: String đã được sanitize (loại bỏ null bytes), hoặc None nếu input là None
    
    Example:
        >>> sanitize_string("Hello\x00World")
        'HelloWorld'
        >>> sanitize_string(None)
        None
    """
    if s is None:
        return None
    if isinstance(s, str):
        # Loại bỏ tất cả null bytes
        return s.replace('\x00', '')
    # Nếu không phải string, convert sang string trước
    return str(s).replace('\x00', '')


def download_attachment_content(redmine: Redmine, attachment_id: int) -> Optional[str]:
    """Tải và decode nội dung text của attachment từ Redmine.
    
    Hàm này tải nội dung attachment từ Redmine API và cố gắng decode thành
    text. Hỗ trợ nhiều encoding (UTF-8, latin-1) và xử lý lỗi gracefully.
    Chỉ nên sử dụng cho text files, không phải binary files.
    
    Quy trình:
    1. Lấy attachment object từ Redmine API
    2. Lấy content URL (có thể là absolute hoặc relative)
    3. Tải content với xác thực API key
    4. Thử decode với nhiều encoding khác nhau
    5. Trả về text content hoặc None nếu thất bại
    
    Args:
        redmine: Redmine client instance đã được khởi tạo
        attachment_id: ID của attachment cần tải
    
    Returns:
        str | None: Nội dung text của attachment nếu thành công, None nếu thất bại
    
    Note:
        - Chỉ nên sử dụng cho text files
        - Timeout được set là 30 giây
        - Nếu không thể decode, sẽ sử dụng 'ignore' errors để tránh crash
    
    Example:
        >>> content = download_attachment_content(redmine, 12345)
        >>> if content:
        ...     print(f"Downloaded {len(content)} characters")
    """
    try:
        attachment = redmine.attachment.get(attachment_id)
        if hasattr(attachment, 'content_url'):
            # Lấy content URL
            content_url = attachment.content_url
            if not content_url.startswith('http'):
                # URL tương đối, cần thêm base URL
                base_url = settings.redmine_url.rstrip('/')
                content_url = base_url + content_url
            
            # Tải với xác thực API key
            headers = {
                'X-Redmine-API-Key': settings.redmine_api_key
            }
            response = requests.get(content_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Thử decode thành text
            try:
                # Thử UTF-8 trước
                content = response.content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # Thử latin-1
                    content = response.content.decode('latin-1')
                except UnicodeDecodeError:
                    # Thử với xử lý lỗi
                    content = response.content.decode('utf-8', errors='ignore')
            
            # Sanitize content để loại bỏ null bytes
            content = sanitize_string(content)
            return content
        else:
            # Thử truy cập content trực tiếp nếu có
            if hasattr(attachment, 'content'):
                return attachment.content
            logger.warning(f"Attachment {attachment_id} has no content_url or content attribute")
            return None
    except Exception as e:
        logger.error(f"Failed to download attachment {attachment_id}: {e}", exc_info=True)
        return None

