"""Router cho OpenAI Config API.

Module này định nghĩa các endpoints cho quản lý cấu hình OpenAI:
- Config CRUD: Create, read, update, delete model configs
- Pricing management: Quản lý pricing cho các models
- Default model: Set và get model mặc định
- Sync defaults: Đồng bộ pricing mặc định từ hardcoded values
"""
from fastapi import APIRouter

from app.api.openai_config.handlers import (
    list_configs,
    get_config,
    create_config,
    update_config,
    delete_config,
    sync_default_pricing,
    get_default_model,
    set_default_model
)

router = APIRouter()

# Đăng ký endpoints
router.add_api_route("", list_configs, methods=["GET"], response_model=list)
router.add_api_route("", create_config, methods=["POST"])
router.add_api_route("/{model_name}", get_config, methods=["GET"])
router.add_api_route("/{model_name}", update_config, methods=["PUT"])
router.add_api_route("/{model_name}", delete_config, methods=["DELETE"])
router.add_api_route("/sync-defaults", sync_default_pricing, methods=["POST"])
router.add_api_route("/default-model", get_default_model, methods=["GET"])
router.add_api_route("/default-model/{model_name}", set_default_model, methods=["POST"])

