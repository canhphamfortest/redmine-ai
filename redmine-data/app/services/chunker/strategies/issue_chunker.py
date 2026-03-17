"""Chiến lược chunking Redmine issue.

Module này cung cấp functions để chia Redmine issue data thành chunks:
- chunk_redmine_issue: Chia issue với xử lý đặc biệt cho metadata, description, journals, attachments
- safe_get: Helper function để safely get values từ nested dictionaries

Tạo metadata chunk riêng để tăng khả năng tìm kiếm.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from app.services.chunker.tokenizer import Tokenizer
from app.services.chunker.strategies.text_chunker import chunk_text

logger = logging.getLogger(__name__)


def safe_get(data, key1, key2, default=None):
    """Lấy giá trị từ dictionary lồng nhau một cách an toàn.
    
    Hàm helper này truy cập giá trị trong nested dictionary mà không gây lỗi
    nếu key không tồn tại hoặc giá trị không phải dictionary. Hữu ích khi
    làm việc với Redmine API responses có cấu trúc lồng nhau và có thể thiếu
    một số fields.
    
    Args:
        data: Dictionary gốc
        key1: Key đầu tiên (outer key)
        key2: Key thứ hai (inner key)
        default: Giá trị mặc định trả về nếu không tìm thấy
    
    Returns:
        Giá trị tại data[key1][key2] nếu tồn tại, hoặc default nếu không
    
    Example:
        >>> issue = {'author': {'name': 'John', 'id': 1}}
        >>> safe_get(issue, 'author', 'name', 'Unknown')
        'John'
        >>> safe_get(issue, 'assignee', 'name', 'Unassigned')
        'Unassigned'
    """
    val = data.get(key1)
    if val and isinstance(val, dict):
        return val.get(key2, default)
    return default


def chunk_redmine_issue(
    issue_data: Dict[str, Any],
    tokenizer: Tokenizer,
    chunk_size: int,
    chunk_overlap: int
) -> List[Dict[str, Any]]:
    """Chia Redmine issue thành các chunk với xử lý đặc biệt cho các thành phần.
    
    Hàm này xử lý Redmine issue một cách toàn diện, tạo chunks từ:
    1. Metadata chunk: Chứa tất cả thông tin metadata (ID, title, status, priority,
       author, dates, relations, etc.) - chunk này có chunk_type='issue_metadata'
    2. Description chunks: Chia description thành các chunk nhỏ hơn
    3. Journal chunks: Chia từng comment/journal entry thành chunks riêng
    4. Attachment chunks: Chia nội dung text của attachments thành chunks
    
    Metadata chunk được tạo đầu tiên và có chunk_type đặc biệt để có thể được
    ưu tiên trong quá trình tìm kiếm.
    
    Args:
        issue_data: Dictionary chứa dữ liệu Redmine issue, bao gồm:
            - id, title, description
            - project, tracker, status, priority
            - author, assignee
            - created_on, updated_on, start_date, due_date
            - done_ratio, estimated_hours, spent_hours
            - children, relations, attachments, watchers
            - custom_fields
            - journals (comments)
        tokenizer: Tokenizer instance để đếm token
        chunk_size: Kích thước tối đa của mỗi chunk (tính bằng token)
        chunk_overlap: Số token chồng chéo giữa các chunk liên tiếp
    
    Returns:
        List[Dict[str, Any]]: Danh sách các chunk được sắp xếp theo thứ tự:
            1. Metadata chunk (chunk_type='issue_metadata', ordinal=0)
            2. Description chunks (chunk_type='issue_description')
            3. Journal chunks (chunk_type='issue_comment')
            4. Attachment chunks (chunk_type='issue_attachment')
        
        Mỗi chunk chứa:
            - ordinal: Thứ tự chunk (int, tăng dần)
            - text_content: Nội dung text (str)
            - token_count: Số lượng token (int)
            - chunk_type: Loại chunk (str)
            - author_id, author_name: Thông tin tác giả (nếu có)
            - journal_id: ID của journal (cho comment chunks)
            - is_private: Có phải private note không (cho comment chunks)
            - heading_title: Tiêu đề (cho attachment chunks)
            - created_on: Thời gian tạo (datetime, cho comment/attachment chunks)
    
    Note:
        - Metadata chunk luôn được tạo đầu tiên (ordinal=0) nếu có metadata
        - Ordinal được tăng dần tuần tự qua tất cả các chunks
        - Chỉ attachments có content text mới được chunk
        - Private notes vẫn được chunk nhưng có flag is_private=True
    """
    chunks = []
    ordinal_counter = 0
    
    # Tạo metadata chunk trước (để có thể tìm kiếm)
    metadata_parts = []
    
    # Thông tin issue cơ bản
    if issue_data.get('id'):
        metadata_parts.append(f"Issue ID: #{issue_data['id']}")
    if issue_data.get('title'):
        metadata_parts.append(f"Title: {issue_data['title']}")
    
    # Thông tin project
    if safe_get(issue_data, 'project', 'name'):
        metadata_parts.append(f"Project: {issue_data['project']['name']}")
    
    # Tracker, Status, Priority
    if safe_get(issue_data, 'tracker', 'name'):
        metadata_parts.append(f"Tracker: {issue_data['tracker']['name']}")
    if safe_get(issue_data, 'status', 'name'):
        metadata_parts.append(f"Status: {issue_data['status']['name']}")
    if safe_get(issue_data, 'priority', 'name'):
        metadata_parts.append(f"Priority: {issue_data['priority']['name']}")
    
    # Người dùng
    if safe_get(issue_data, 'author', 'name'):
        metadata_parts.append(f"Author: {issue_data['author']['name']}")
    if safe_get(issue_data, 'assignee', 'name'):
        metadata_parts.append(f"Assigned to: {issue_data['assignee']['name']}")
    
    # Category và Version
    category = issue_data.get('category')
    if category and isinstance(category, dict) and category.get('name'):
        metadata_parts.append(f"Category: {category['name']}")
    
    fixed_version = issue_data.get('fixed_version')
    if fixed_version and isinstance(fixed_version, dict) and fixed_version.get('name'):
        metadata_parts.append(f"Target Version: {fixed_version['name']}")
    
    # Ngày tháng
    if issue_data.get('created_on'):
        metadata_parts.append(f"Created: {issue_data['created_on']}")
    if issue_data.get('updated_on'):
        metadata_parts.append(f"Updated: {issue_data['updated_on']}")
    if issue_data.get('start_date'):
        metadata_parts.append(f"Start Date: {issue_data['start_date']}")
    if issue_data.get('due_date'):
        metadata_parts.append(f"Due Date: {issue_data['due_date']}")
    
    # Tiến độ và theo dõi thời gian
    if issue_data.get('done_ratio') is not None:
        metadata_parts.append(f"Progress: {issue_data['done_ratio']}%")
    if issue_data.get('estimated_hours'):
        metadata_parts.append(f"Estimated Hours: {issue_data['estimated_hours']}")
    if issue_data.get('spent_hours'):
        metadata_parts.append(f"Spent Hours: {issue_data['spent_hours']}")
    
    # Issues liên quan
    if issue_data.get('children'):
        children_count = len(issue_data['children'])
        children_subjects = [c.get('subject', f"#{c.get('id')}") for c in issue_data['children'][:5]]
        children_text = f"Sub-issues ({children_count}): {', '.join(children_subjects)}"
        if children_count > 5:
            children_text += f" and {children_count - 5} more"
        metadata_parts.append(children_text)
    
    if issue_data.get('relations'):
        relations_text = "Related Issues: "
        relation_parts = []
        for rel in issue_data['relations'][:5]:
            rel_type = rel.get('relation_type', 'related')
            issue_to_id = rel.get('issue_to_id') or rel.get('issue_id')
            relation_parts.append(f"{rel_type} #{issue_to_id}")
        relations_text += ", ".join(relation_parts)
        if len(issue_data['relations']) > 5:
            relations_text += f" and {len(issue_data['relations']) - 5} more"
        metadata_parts.append(relations_text)
    
    # Attachments
    if issue_data.get('attachments'):
        attachments_count = len(issue_data['attachments'])
        attachment_names = [a.get('filename', 'unnamed') for a in issue_data['attachments'][:3]]
        attachments_text = f"Attachments ({attachments_count}): {', '.join(attachment_names)}"
        if attachments_count > 3:
            attachments_text += f" and {attachments_count - 3} more"
        metadata_parts.append(attachments_text)
    
    # Watchers
    if issue_data.get('watchers'):
        watchers_count = len(issue_data['watchers'])
        watcher_names = [w.get('name') for w in issue_data['watchers'][:5] if w.get('name')]
        watchers_text = f"Watchers ({watchers_count}): {', '.join(watcher_names)}"
        if watchers_count > 5:
            watchers_text += f" and {watchers_count - 5} more"
        metadata_parts.append(watchers_text)
    
    # Custom fields
    if issue_data.get('custom_fields'):
        for custom_field in issue_data['custom_fields']:
            field_name = custom_field.get('name', 'Unknown')
            field_value = custom_field.get('value')
            if field_value:
                if isinstance(field_value, list):
                    field_value = ', '.join(str(v) for v in field_value)
                metadata_parts.append(f"{field_name}: {field_value}")
    
    if metadata_parts:
        metadata_text = "\n".join(metadata_parts)
        metadata_chunk = {
            'ordinal': ordinal_counter,
            'text_content': metadata_text,
            'token_count': tokenizer.token_length(metadata_text),
            'chunk_type': 'issue_metadata',
            'author_id': safe_get(issue_data, 'author', 'id'),
            'author_name': safe_get(issue_data, 'author', 'name'),
        }
        chunks.append(metadata_chunk)
        ordinal_counter += 1
    
    # Description chính
    if issue_data.get('description'):
        desc_chunks = chunk_text(
            issue_data['description'],
            tokenizer,
            chunk_size,
            chunk_overlap,
            metadata={
                'chunk_type': 'issue_description',
                'author_id': issue_data.get('author', {}).get('id'),
                'author_name': issue_data.get('author', {}).get('name'),
            },
            chunk_type='issue_description'
        )
        # Cập nhật ordinal để tuần tự qua tất cả các chunks
        for chunk in desc_chunks:
            chunk['ordinal'] = ordinal_counter
            ordinal_counter += 1
        chunks.extend(desc_chunks)
    
    # Journals (comments)
    if issue_data.get('journals'):
        for journal in issue_data['journals']:
            if journal.get('notes'):
                journal_chunks = chunk_text(
                    journal['notes'],
                    tokenizer,
                    chunk_size,
                    chunk_overlap,
                    metadata={
                        'chunk_type': 'issue_comment',
                        'journal_id': journal.get('id'),
                        'author_id': journal.get('user', {}).get('id'),
                        'author_name': journal.get('user', {}).get('name'),
                        'created_on': journal.get('created_on'),
                        'is_private': journal.get('private_notes', False),
                    },
                    chunk_type='issue_comment'
                )
                # Cập nhật ordinal để tuần tự qua tất cả các chunks
                for chunk in journal_chunks:
                    chunk['ordinal'] = ordinal_counter
                    ordinal_counter += 1
                chunks.extend(journal_chunks)
    
    # Attachments (chỉ các file text)
    if issue_data.get('attachments'):
        for attachment in issue_data['attachments']:
            if attachment.get('content'):
                # Xây dựng văn bản attachment với metadata
                attachment_text_parts = []
                filename = attachment.get('filename', 'unnamed')
                attachment_text_parts.append(f"Attachment: {filename}")
                if attachment.get('description'):
                    attachment_text_parts.append(f"Description: {attachment.get('description')}")
                attachment_text_parts.append("")
                attachment_text_parts.append(attachment['content'])
                
                attachment_text = "\n".join(attachment_text_parts)
                
                # Parse created_on nếu nó là string
                created_on = attachment.get('created_on')
                if created_on and isinstance(created_on, str):
                    try:
                        created_on = datetime.fromisoformat(created_on.replace('Z', '+00:00'))
                    except:
                        created_on = None
                
                attachment_chunks = chunk_text(
                    attachment_text,
                    tokenizer,
                    chunk_size,
                    chunk_overlap,
                    metadata={
                        'chunk_type': 'issue_attachment',
                        'heading_title': f"Attachment: {filename}",
                        'author_id': attachment.get('author', {}).get('id'),
                        'author_name': attachment.get('author', {}).get('name'),
                        'created_on': created_on,
                    },
                    chunk_type='issue_attachment'
                )
                # Cập nhật ordinal để tuần tự qua tất cả các chunks
                for chunk in attachment_chunks:
                    chunk['ordinal'] = ordinal_counter
                    ordinal_counter += 1
                chunks.extend(attachment_chunks)
    
    return chunks

