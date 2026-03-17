"""Module service cache.

Module này cung cấp Redis cache service cho ứng dụng:
- RedisCache: Class chính quản lý Redis connection và operations
- cache: Singleton instance được sử dụng trong toàn bộ ứng dụng

Các chức năng chính:
- RAG response caching: Cache responses từ RAG search để giảm API calls
- Embedding caching: Cache embeddings để tránh tính toán lại
- TTL management: Quản lý thời gian sống của cache entries
- Connection management: Tự động reconnect khi mất kết nối
"""
from app.services.cache.cache import cache, RedisCache

__all__ = ['cache', 'RedisCache']

