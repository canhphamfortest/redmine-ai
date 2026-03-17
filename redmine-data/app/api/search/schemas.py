"""Pydantic schemas cho search API.

Module này định nghĩa các request/response schemas cho search endpoints:
- SearchRequest: Schema cho vector search request
- RAGRequest: Schema cho RAG search request
- GenerateRequest: Schema cho AI text generation request (không có retrieval)
"""
from pydantic import BaseModel
from typing import Optional


class SearchRequest(BaseModel):
    """Schema cho request vector search.
    
    Attributes:
        query: Query text để tìm kiếm (str)
        top_k: Số lượng kết quả tối đa cần trả về (int, default: 5).
              Càng lớn thì càng nhiều kết quả nhưng có thể chậm hơn
        list_project_ids: Danh sách project IDs để filter kết quả (str, optional).
                         Format: "id1,id2,id3" - các ID cách nhau bởi dấu phẩy
        user_id: ID của user thực hiện search (str, optional)
    """
    query: str
    top_k: Optional[int] = 5
    list_project_ids: Optional[str] = None
    user_id: Optional[str] = None


class RAGRequest(BaseModel):
    """Schema cho request RAG search.
    
    Attributes:
        query: Query text để tìm kiếm và generate answer (str).
              Query này sẽ được sử dụng để retrieve chunks và generate answer bằng AI
        list_project_ids: Danh sách project IDs để filter kết quả (str, optional).
                         Format: "id1,id2,id3" - các ID cách nhau bởi dấu phẩy
        user_id: ID của user thực hiện search (str, optional)
    """
    query: str
    list_project_ids: Optional[str] = None
    user_id: Optional[str] = None


class GenerateRequest(BaseModel):
    """Schema cho request AI text generation (không có retrieval).
    
    Attributes:
        prompt: Prompt đầy đủ để gửi đến AI (str).
              Prompt này sẽ được sử dụng trực tiếp để generate answer,
              không có vector search hay reranking
        user_id: ID của user thực hiện search (str, optional)
    """
    prompt: str
    user_id: Optional[str] = None

