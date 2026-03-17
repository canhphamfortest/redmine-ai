"""Chiến lược chunking Redmine wiki"""
import logging
from typing import List, Dict, Any

from app.services.chunker.tokenizer import Tokenizer
from app.services.chunker.strategies.text_chunker import chunk_text

logger = logging.getLogger(__name__)


def chunk_redmine_wiki(
    wiki_data: Dict[str, Any],
    tokenizer: Tokenizer,
    chunk_size: int,
    chunk_overlap: int
) -> List[Dict[str, Any]]:
    """Chia Redmine wiki page thành chunks với xử lý đặc biệt cho metadata.
    
    Hàm này xử lý đặc biệt cho Redmine wiki page data:
    - Tạo một chunk metadata riêng chứa thông tin quan trọng (title, project, author, version, dates, parent, comments)
    - Chia text content thành các chunks với overlap
    
    Args:
        wiki_data: Dictionary chứa dữ liệu Redmine wiki page (dict):
            - title: Tiêu đề wiki page (str)
            - text: Nội dung wiki page (str)
            - version: Phiên bản wiki page (int, optional)
            - author: Thông tin tác giả (dict với id, name, optional)
            - project: Thông tin project (dict với name, optional)
            - created_on: Ngày tạo (str, ISO format, optional)
            - updated_on: Ngày cập nhật (str, ISO format, optional)
            - parent: Thông tin trang cha (dict với title, optional)
            - comments: Comments của wiki page (str, optional)
        tokenizer: Tokenizer instance để đếm tokens (Tokenizer)
        chunk_size: Kích thước tối đa của mỗi chunk (tính bằng token) (int)
        chunk_overlap: Số lượng token chồng lấn giữa các chunk liên tiếp (int)
    
    Returns:
        List[Dict[str, Any]]: Danh sách các chunk, mỗi chunk chứa:
            - ordinal: Thứ tự của chunk (int, 0-based)
            - text_content: Nội dung văn bản của chunk (str)
            - token_count: Số lượng tokens trong chunk (int)
            - chunk_type: Loại chunk ("wiki_metadata" hoặc "wiki_content") (str)
            - author_id: ID tác giả (int, optional)
            - author_name: Tên tác giả (str, optional)
            - wiki_version: Phiên bản wiki (int, optional)
    
    Note:
        - Metadata chunk được đặt đầu tiên (ordinal=0) để tăng khả năng tìm kiếm
        - Text content được chia bằng chunk_text() với overlap
        - Ordinals được đánh số tuần tự qua tất cả chunks
        - Metadata chunk chứa đầy đủ thông tin wiki để tìm kiếm nhanh
    """
    chunks = []
    ordinal_counter = 0
    
    # Tạo metadata chunk trước (để có thể tìm kiếm)
    metadata_parts = []
    
    # Thông tin wiki cơ bản
    if wiki_data.get('title'):
        metadata_parts.append(f"Wiki Page: {wiki_data['title']}")
    
    # Thông tin project
    if wiki_data.get('project', {}).get('name'):
        metadata_parts.append(f"Project: {wiki_data['project']['name']}")
    
    # Tác giả
    if wiki_data.get('author', {}).get('name'):
        metadata_parts.append(f"Author: {wiki_data['author']['name']}")
    
    # Phiên bản
    if wiki_data.get('version'):
        metadata_parts.append(f"Version: {wiki_data['version']}")
    
    # Ngày tháng
    if wiki_data.get('created_on'):
        metadata_parts.append(f"Created: {wiki_data['created_on']}")
    if wiki_data.get('updated_on'):
        metadata_parts.append(f"Updated: {wiki_data['updated_on']}")
    
    # Trang cha
    parent = wiki_data.get('parent')
    if parent and isinstance(parent, dict) and parent.get('title'):
        metadata_parts.append(f"Parent Page: {parent['title']}")
    
    # Comments
    if wiki_data.get('comments'):
        metadata_parts.append(f"Comments: {wiki_data['comments']}")
    
    if metadata_parts:
        metadata_text = "\n".join(metadata_parts)
        metadata_chunk = {
            'ordinal': ordinal_counter,
            'text_content': metadata_text,
            'token_count': tokenizer.token_length(metadata_text),
            'chunk_type': 'wiki_metadata',
            'author_id': wiki_data.get('author', {}).get('id'),
            'author_name': wiki_data.get('author', {}).get('name'),
            'wiki_version': wiki_data.get('version'),
        }
        chunks.append(metadata_chunk)
        ordinal_counter += 1
    
    # Nội dung văn bản wiki chính
    if wiki_data.get('text'):
        text_chunks = chunk_text(
            wiki_data['text'],
            tokenizer,
            chunk_size,
            chunk_overlap,
            metadata={
                'chunk_type': 'wiki_content',
                'author_id': wiki_data.get('author', {}).get('id'),
                'author_name': wiki_data.get('author', {}).get('name'),
                'wiki_version': wiki_data.get('version'),
            },
            chunk_type='wiki_content'
        )
        # Cập nhật ordinal để tuần tự qua tất cả các chunks
        for chunk in text_chunks:
            chunk['ordinal'] = ordinal_counter
            ordinal_counter += 1
        chunks.extend(text_chunks)
    
    return chunks

