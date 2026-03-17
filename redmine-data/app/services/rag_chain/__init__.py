"""Module RAG chain.

Module này cung cấp RAG (Retrieval-Augmented Generation) chain service:
- RAGChain: Class chính thực hiện RAG pipeline
- rag_chain: Singleton instance được sử dụng trong toàn bộ ứng dụng

RAG pipeline bao gồm:
1. Retrieve: Tìm kiếm chunks liên quan bằng vector similarity
2. Augment: Xây dựng context từ chunks
3. Generate: Tạo câu trả lời bằng OpenAI API
"""
from app.services.rag_chain.chain import RAGChain

# Singleton instance
rag_chain = RAGChain()

__all__ = ['RAGChain', 'rag_chain']

