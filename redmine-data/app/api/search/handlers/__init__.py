"""Các handler Search API.

Module này export tất cả handlers cho Search API endpoints:
- Search: vector_search, rag_search, generate_text
- Related issues: find_related_issues
- Analytics: get_search_analytics, get_search_history
- Usage: get_openai_usage, get_billing_cycle_usage

Tất cả handlers được import từ các submodules và export qua __all__.
"""
from app.api.search.handlers.vector_search import vector_search
from app.api.search.handlers.rag_search import rag_search
from app.api.search.handlers.generate_text import generate_text
from app.api.search.handlers.history import get_search_history
from app.api.search.handlers.analytics import get_search_analytics
from app.api.search.handlers.usage import get_openai_usage, get_billing_cycle_usage
from app.api.search.handlers.related_issues import find_related_issues

__all__ = [
    'vector_search',
    'rag_search',
    'generate_text',
    'get_search_history',
    'get_search_analytics',
    'get_openai_usage',
    'get_billing_cycle_usage',
    'find_related_issues'
]

