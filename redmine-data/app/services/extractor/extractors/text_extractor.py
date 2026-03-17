"""Trích xuất file văn bản.

Module này cung cấp các functions để trích xuất text từ các file văn bản:
- extract_text: Trích xuất từ plain text files (.txt)
- extract_markdown: Trích xuất từ Markdown files (.md)
- extract_json: Trích xuất từ JSON files (format thành readable text)
- extract_html: Trích xuất từ HTML files (sử dụng BeautifulSoup)

Mỗi function trả về dictionary với 'content' và 'metadata' fields.
"""
from typing import Dict, Any
import json
import markdown
from bs4 import BeautifulSoup


def extract_text(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung từ file text thuần (plain text).
    
    Hàm này đọc file text với encoding UTF-8 và trả về nội dung. Sử dụng
    errors='ignore' để xử lý các ký tự không hợp lệ.
    
    Args:
        file_path: Đường dẫn đến file text cần đọc (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): Nội dung text đã được strip()
            - metadata (dict): Dictionary rỗng (không có metadata cho text files)
    
    Note:
        - Encoding mặc định là UTF-8
        - Các ký tự không hợp lệ sẽ bị bỏ qua (errors='ignore')
        - Content được strip() để loại bỏ whitespace thừa
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    return {
        'content': content.strip(),
        'metadata': {},
    }


def extract_markdown(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung từ file Markdown và chuyển đổi sang text thuần.
    
    Hàm này đọc file Markdown, chuyển đổi sang HTML, sau đó loại bỏ tất cả
    HTML tags để lấy text thuần. Giữ lại markdown_raw để có thể sử dụng sau.
    
    Quy trình:
    1. Đọc file Markdown
    2. Chuyển đổi Markdown sang HTML bằng markdown library
    3. Parse HTML và extract text bằng BeautifulSoup
    4. Loại bỏ tất cả HTML tags
    
    Args:
        file_path: Đường dẫn đến file Markdown cần trích xuất (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): Nội dung text thuần đã loại bỏ Markdown syntax
            - metadata (dict): Dictionary rỗng
            - markdown_raw (str): Nội dung Markdown gốc (chưa xử lý)
    
    Note:
        - Encoding mặc định là UTF-8
        - Markdown syntax (**, #, etc.) sẽ bị loại bỏ
        - Cấu trúc (headings, lists) được giữ lại dưới dạng text
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Chuyển đổi sang HTML trước
    html = markdown.markdown(md_content)
    
    # Loại bỏ thẻ HTML
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    return {
        'content': text.strip(),
        'metadata': {},
        'markdown_raw': md_content
    }


def extract_json(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung từ file JSON và format thành text dễ đọc.
    
    Hàm này đọc file JSON, parse thành Python object, sau đó format lại
    thành JSON string với indentation để dễ đọc. Giữ lại json_data để
    có thể truy cập structured data sau.
    
    Args:
        file_path: Đường dẫn đến file JSON cần trích xuất (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): JSON string đã được format với indentation
            - metadata (dict): Dictionary rỗng
            - json_data: Python object (dict/list) đã được parse từ JSON
    
    Raises:
        json.JSONDecodeError: Nếu file không phải là JSON hợp lệ
    
    Note:
        - Encoding mặc định là UTF-8
        - JSON được format với indent=2 và ensure_ascii=False
        - json_data có thể được sử dụng để truy cập structured data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Chuyển đổi sang văn bản dễ đọc
    content = json.dumps(data, indent=2, ensure_ascii=False)
    
    return {
        'content': content,
        'metadata': {},
        'json_data': data
    }


def extract_html(file_path: str) -> Dict[str, Any]:
    """Trích xuất nội dung text từ file HTML, loại bỏ HTML tags và scripts.
    
    Hàm này đọc file HTML, parse bằng BeautifulSoup, loại bỏ các phần tử
    script và style, sau đó extract text và làm sạch whitespace.
    
    Quy trình:
    1. Đọc file HTML
    2. Parse HTML bằng BeautifulSoup
    3. Loại bỏ các phần tử <script> và <style>
    4. Extract text và làm sạch whitespace (loại bỏ khoảng trắng thừa)
    5. Trích xuất title nếu có
    
    Args:
        file_path: Đường dẫn đến file HTML cần trích xuất (string)
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - content (str): Nội dung text đã được làm sạch
            - metadata (dict): Dictionary chứa title nếu có
    
    Note:
        - Encoding mặc định là UTF-8
        - Scripts và styles được loại bỏ hoàn toàn
        - Whitespace được làm sạch (loại bỏ khoảng trắng thừa, empty lines)
        - Title được trích xuất từ <title> tag nếu có
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Loại bỏ các phần tử script và style
    for script in soup(["script", "style"]):
        script.decompose()
    
    text = soup.get_text()
    
    # Làm sạch khoảng trắng
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return {
        'content': text,
        'metadata': {
            'title': soup.title.string if soup.title else None
        }
    }

