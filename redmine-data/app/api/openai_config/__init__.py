"""Module OpenAI Config API.

Module này cung cấp các endpoints cho quản lý cấu hình OpenAI:
- Config CRUD: Create, read, update, delete model configs
- Pricing management: Quản lý pricing cho các OpenAI models
- Default model: Set và get model mặc định cho AI calls
- Sync defaults: Đồng bộ pricing mặc định từ hardcoded values vào database

Cho phép quản lý pricing và model selection trong database thay vì hardcode.

Tất cả endpoints được định nghĩa trong router và được mount tại /api/openai-config.
"""
from app.api.openai_config.router import router

__all__ = ['router']

