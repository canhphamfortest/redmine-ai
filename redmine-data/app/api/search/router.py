"""Router cho Search API.

Module này định nghĩa các endpoints cho tìm kiếm và analytics:
- Vector search: Tìm kiếm semantic bằng vector embeddings
- RAG search: Tìm kiếm với RAG (Retrieval-Augmented Generation)
- Generate text: Tạo text bằng AI trực tiếp (không có retrieval)
- Related issues: Tìm các issues liên quan
- Analytics: Thống kê tìm kiếm và usage
- History: Lịch sử tìm kiếm
"""
from fastapi import APIRouter

from app.api.search.handlers import (
    vector_search,
    rag_search,
    generate_text,
    get_search_history,
    get_search_analytics,
    get_openai_usage,
    get_billing_cycle_usage,
    find_related_issues
)

router = APIRouter()

# Đăng ký endpoints
router.add_api_route("/vector", vector_search, methods=["POST"])
router.add_api_route("/rag", rag_search, methods=["POST"])
router.add_api_route("/generate", generate_text, methods=["POST"])
router.add_api_route("/history", get_search_history, methods=["GET"])
router.add_api_route("/analytics", get_search_analytics, methods=["GET"])
router.add_api_route("/usage", get_openai_usage, methods=["GET"])
router.add_api_route("/usage/billing-cycles", get_billing_cycle_usage, methods=["GET"])
router.add_api_route("/issues/{issue_id}/related", find_related_issues, methods=["GET"])

