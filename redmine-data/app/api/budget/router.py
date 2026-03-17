"""Router cho Budget API."""
from fastapi import APIRouter

from app.api.budget.handlers import (
    list_budget_configs,
    get_budget_config,
    create_budget_config,
    update_budget_config,
    delete_budget_config,
    get_budget_status,
    get_budget_status_by_provider,
    list_alerts,
    acknowledge_alert
)
from app.api.budget.schemas import (
    BudgetConfigResponse,
    BudgetConfigCreate,
    BudgetConfigUpdate,
    BudgetStatusListResponse,
    BudgetStatusResponse,
    BudgetAlertResponse
)

router = APIRouter()

# Budget Config endpoints
router.add_api_route(
    "/configs",
    list_budget_configs,
    methods=["GET"],
    response_model=list[BudgetConfigResponse],
    summary="List budget configs"
)
router.add_api_route(
    "/configs",
    create_budget_config,
    methods=["POST"],
    response_model=BudgetConfigResponse,
    summary="Create budget config"
)
router.add_api_route(
    "/configs/{config_id}",
    get_budget_config,
    methods=["GET"],
    response_model=BudgetConfigResponse,
    summary="Get budget config"
)
router.add_api_route(
    "/configs/{config_id}",
    update_budget_config,
    methods=["PUT"],
    response_model=BudgetConfigResponse,
    summary="Update budget config"
)
router.add_api_route(
    "/configs/{config_id}",
    delete_budget_config,
    methods=["DELETE"],
    summary="Delete budget config"
)

# Budget Status endpoints
router.add_api_route(
    "/status",
    get_budget_status,
    methods=["GET"],
    response_model=BudgetStatusListResponse,
    summary="Get budget status for all providers"
)
router.add_api_route(
    "/status/{provider}",
    get_budget_status_by_provider,
    methods=["GET"],
    response_model=BudgetStatusResponse,
    summary="Get budget status for specific provider"
)

# Budget Alerts endpoints
router.add_api_route(
    "/alerts",
    list_alerts,
    methods=["GET"],
    response_model=list[BudgetAlertResponse],
    summary="List budget alerts"
)
router.add_api_route(
    "/alerts/{alert_id}/acknowledge",
    acknowledge_alert,
    methods=["POST"],
    summary="Acknowledge budget alert"
)

# Budget Check endpoint (for scheduler)
from app.api.budget.handlers.check import check_budget_thresholds_endpoint
router.add_api_route(
    "/check",
    check_budget_thresholds_endpoint,
    methods=["POST"],
    summary="Check budget thresholds and trigger alerts (for scheduler)"
)
