"""Các handler OpenAI Config API.

Module này export tất cả handlers cho OpenAI Config API endpoints:
- CRUD handlers: list_configs, get_config, create_config, update_config, delete_config
- Default model handlers: get_default_model, set_default_model
- Sync handlers: sync_default_pricing

Tất cả handlers được import từ các submodules và export qua __all__.
"""
from app.api.openai_config.handlers.crud import (
    list_configs,
    get_config,
    create_config,
    update_config,
    delete_config
)
from app.api.openai_config.handlers.defaults import (
    sync_default_pricing,
    get_default_model,
    set_default_model
)

__all__ = [
    'list_configs',
    'get_config',
    'create_config',
    'update_config',
    'delete_config',
    'sync_default_pricing',
    'get_default_model',
    'set_default_model'
]

