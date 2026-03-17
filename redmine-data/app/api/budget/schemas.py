"""Pydantic schemas cho Budget API."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class BudgetConfigCreate(BaseModel):
    """Schema cho request tạo budget config.
    
    Attributes:
        provider: Provider name (openai, google, anthropic, groq)
        budget_amount_usd: Số tiền budget tính bằng USD
        invoice_day: Ngày invoice trong tháng (1-31)
        alert_thresholds: Danh sách các ngưỡng cảnh báo (ví dụ: [50, 80, 100])
        is_active: Budget có active không (default: True)
    """
    provider: str = Field(..., description="Provider name (openai, google, anthropic, groq)")
    budget_amount_usd: float = Field(..., gt=0, description="Budget amount in USD")
    invoice_day: int = Field(..., ge=1, le=31, description="Invoice day of month (1-31)")
    alert_thresholds: List[int] = Field(..., description="Alert thresholds as percentages (e.g., [50, 80, 100])")
    is_active: bool = Field(default=True, description="Whether budget is active")
    
    @field_validator('alert_thresholds')
    @classmethod
    def validate_thresholds(cls, v):
        if not v:
            raise ValueError("alert_thresholds cannot be empty")
        if not all(0 < t <= 100 for t in v):
            raise ValueError("All thresholds must be between 1 and 100")
        if len(v) != len(set(v)):
            raise ValueError("Thresholds must be unique")
        return sorted(v)


class BudgetConfigUpdate(BaseModel):
    """Schema cho request cập nhật budget config (partial update).
    
    Attributes:
        budget_amount_usd: Budget amount mới (optional)
        invoice_day: Invoice day mới (optional)
        alert_thresholds: Alert thresholds mới (optional)
        is_active: Trạng thái active mới (optional)
    """
    budget_amount_usd: Optional[float] = Field(None, gt=0, description="Budget amount in USD")
    invoice_day: Optional[int] = Field(None, ge=1, le=31, description="Invoice day of month (1-31)")
    alert_thresholds: Optional[List[int]] = Field(None, description="Alert thresholds as percentages")
    is_active: Optional[bool] = Field(None, description="Whether budget is active")
    
    @field_validator('alert_thresholds')
    @classmethod
    def validate_thresholds(cls, v):
        if v is not None:
            if not v:
                raise ValueError("alert_thresholds cannot be empty")
            if not all(0 < t <= 100 for t in v):
                raise ValueError("All thresholds must be between 1 and 100")
            if len(v) != len(set(v)):
                raise ValueError("Thresholds must be unique")
            return sorted(v)
        return v


class BudgetConfigResponse(BaseModel):
    """Schema cho response budget config.
    
    Attributes:
        id: UUID của config
        provider: Provider name
        budget_amount_usd: Budget amount
        invoice_day: Invoice day
        alert_thresholds: Alert thresholds
        is_active: Trạng thái active
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    id: str
    provider: str
    budget_amount_usd: float
    invoice_day: int
    alert_thresholds: List[int]
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class BudgetStatusResponse(BaseModel):
    """Schema cho response budget status.
    
    Attributes:
        provider: Provider name
        budget_config_id: ID của budget config
        budget_amount_usd: Budget amount
        current_spending_usd: Chi phí hiện tại
        remaining_budget_usd: Budget còn lại
        percentage_used: Phần trăm đã sử dụng
        billing_cycle_start: Ngày bắt đầu billing cycle
        billing_cycle_end: Ngày kết thúc billing cycle
        invoice_day: Invoice day
        alert_thresholds: Alert thresholds
        is_active: Trạng thái active
    """
    provider: str
    budget_config_id: str
    budget_amount_usd: float
    current_spending_usd: float
    remaining_budget_usd: float
    percentage_used: float
    billing_cycle_start: str
    billing_cycle_end: str
    invoice_day: int
    alert_thresholds: List[int]
    is_active: bool


class BudgetStatusListResponse(BaseModel):
    """Schema cho response danh sách budget status.
    
    Attributes:
        statuses: Danh sách budget status
        total_providers: Tổng số providers
    """
    statuses: List[BudgetStatusResponse]
    total_providers: int


class BudgetAlertResponse(BaseModel):
    """Schema cho response budget alert.
    
    Attributes:
        id: UUID của alert
        budget_config_id: ID của budget config
        provider: Provider name
        billing_cycle_start: Ngày bắt đầu billing cycle
        billing_cycle_end: Ngày kết thúc billing cycle
        threshold_percentage: Ngưỡng đã trigger
        current_spending_usd: Chi phí hiện tại khi trigger
        budget_amount_usd: Budget amount tại thời điểm trigger
        alert_type: Loại alert (threshold_reached, budget_exceeded)
        alert_channels: Các kênh đã gửi
        sent_at: Thời gian gửi alert
        acknowledged_at: Thời gian acknowledge (optional)
        created_at: Thời gian tạo
    """
    id: str
    budget_config_id: str
    provider: str
    billing_cycle_start: str
    billing_cycle_end: str
    threshold_percentage: int
    current_spending_usd: float
    budget_amount_usd: float
    alert_type: str
    alert_channels: List[str]
    sent_at: str
    acknowledged_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True
