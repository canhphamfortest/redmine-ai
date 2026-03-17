"""Các tiện ích phát hiện loại file và ngôn ngữ.

Module này cung cấp functions để phát hiện file types và programming languages:
- detect_file_type: Phát hiện loại file (code, documentation, text, etc.)
- detect_language: Phát hiện programming language dựa trên file extension

Sử dụng file extensions để xác định file type và language cho chunking strategy phù hợp.
"""
from pathlib import Path


def detect_file_type(file_path: Path) -> str:
    """Phát hiện loại file từ phần mở rộng.
    
    Hàm này phân loại file thành các loại: code, documentation, text, data, config.
    Dựa trên file extension để xác định loại.
    
    Args:
        file_path: Đường dẫn đến file (Path)
    
    Returns:
        str: Loại file ('code', 'documentation', 'text', 'data', 'config', 'unknown')
    
    Note:
        - Code files: .py, .js, .java, .cpp, .c, .go, .rs
        - Documentation: .md
        - Text: .txt
        - Data: .json
        - Config: .yaml, .yml
        - Unknown: Các extension khác
    """
    ext_map = {
        '.py': 'code',
        '.js': 'code',
        '.java': 'code',
        '.cpp': 'code',
        '.c': 'code',
        '.go': 'code',
        '.rs': 'code',
        '.md': 'documentation',
        '.txt': 'text',
        '.json': 'data',
        '.yaml': 'config',
        '.yml': 'config',
    }
    return ext_map.get(file_path.suffix.lower(), 'unknown')


def detect_language(file_path: Path) -> str:
    """Phát hiện ngôn ngữ lập trình từ phần mở rộng file.
    
    Hàm này map file extension sang tên ngôn ngữ lập trình để sử dụng
    với code chunker. Chỉ trả về ngôn ngữ cho code files.
    
    Args:
        file_path: Đường dẫn đến file (Path)
    
    Returns:
        str | None: Tên ngôn ngữ lập trình nếu là code file, None nếu không phải
    
    Note:
        - Hỗ trợ: python, javascript, java, cpp, go, rust, ruby, php
        - .c được map thành 'cpp' (C/C++)
        - Chỉ code files mới có language, text files trả về None
    """
    lang_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'cpp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
    }
    return lang_map.get(file_path.suffix.lower())

