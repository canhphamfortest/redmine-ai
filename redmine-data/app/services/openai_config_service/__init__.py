"""Module LLM Config Service.

Module này cung cấp service để quản lý cấu hình pricing và model mặc định cho OpenAI:
- OpenAIConfigService: Class chính cung cấp các phương thức:
  - CRUD operations cho configs
  - Quản lý model mặc định
  - Sync pricing từ hardcoded values
  - Lấy pricing cho models

Cho phép quản lý pricing trong database thay vì hardcode, hỗ trợ:
- Custom pricing cho từng model
- Activate/deactivate models
- Set default model
- Sync pricing mặc định
"""
from app.services.openai_config_service.service import LLMConfigService, OpenAIConfigService

__all__ = ['LLMConfigService', 'OpenAIConfigService']

