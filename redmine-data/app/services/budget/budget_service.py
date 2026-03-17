"""Budget service để tính toán spending và check thresholds."""
import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange

from app.models import BudgetConfig, LLMUsageLog
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class BudgetService:
    """Service để quản lý budget và tính toán spending."""
    
    @staticmethod
    def get_current_billing_cycle(invoice_day: int) -> Tuple[datetime, datetime]:
        """Tính toán billing cycle hiện tại dựa trên invoice_day.
        
        Args:
            invoice_day: Ngày invoice trong tháng (1-31)
        
        Returns:
            Tuple[datetime, datetime]: (cycle_start, cycle_end) trong UTC
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        # Nếu hôm nay trước ngày invoice, sử dụng ngày invoice của tháng trước
        if now.day < invoice_day:
            last_month = now - relativedelta(months=1)
            cycle_start = datetime(last_month.year, last_month.month, invoice_day)
        else:
            cycle_start = datetime(current_year, current_month, invoice_day)
        
        # Cycle end là ngày invoice của tháng tiếp theo
        cycle_end = cycle_start + relativedelta(months=1)
        
        # Điều chỉnh nếu ngày invoice không tồn tại trong tháng tiếp theo
        if cycle_end.day != invoice_day:
            last_day = monthrange(cycle_end.year, cycle_end.month)[1]
            if invoice_day > last_day:
                cycle_end = datetime(cycle_end.year, cycle_end.month, last_day)
            else:
                cycle_end = datetime(cycle_end.year, cycle_end.month, invoice_day)
        
        # Đảm bảo timezone aware (UTC)
        from datetime import timezone as tz
        if cycle_start.tzinfo is None:
            cycle_start = cycle_start.replace(tzinfo=tz.utc)
        if cycle_end.tzinfo is None:
            cycle_end = cycle_end.replace(tzinfo=tz.utc)
        
        return cycle_start, cycle_end
    
    @staticmethod
    def get_current_spending(
        provider: str,
        invoice_day: int,
        db: Optional[Session] = None
    ) -> float:
        """Tính toán chi phí hiện tại trong billing cycle.
        
        Args:
            provider: Provider name (openai, google, anthropic, groq)
            invoice_day: Ngày invoice trong tháng
            db: Database session (tùy chọn)
        
        Returns:
            float: Chi phí hiện tại tính bằng USD
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            cycle_start, cycle_end = BudgetService.get_current_billing_cycle(invoice_day)
            
            # Query tổng chi phí trong billing cycle
            result = db.query(
                func.sum(LLMUsageLog.cost_usd).label('total_cost')
            ).filter(
                LLMUsageLog.provider == provider,
                LLMUsageLog.created_at >= cycle_start,
                LLMUsageLog.created_at < cycle_end
            ).first()
            
            return float(result.total_cost or 0.0)
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_budget_status(
        provider: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Lấy trạng thái budget hiện tại.
        
        Args:
            provider: Provider name (tùy chọn). Nếu None, lấy tất cả providers
            db: Database session (tùy chọn)
        
        Returns:
            Dict[str, Any]: Dictionary chứa budget status cho từng provider:
                - provider: Provider name
                - budget_amount_usd: Budget amount
                - current_spending_usd: Chi phí hiện tại
                - remaining_budget_usd: Budget còn lại
                - percentage_used: Phần trăm đã sử dụng
                - billing_cycle_start: Ngày bắt đầu cycle
                - billing_cycle_end: Ngày kết thúc cycle
                - is_active: Budget có active không
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Query budget configs
            query = db.query(BudgetConfig).filter(BudgetConfig.is_active == True)
            if provider:
                query = query.filter(BudgetConfig.provider == provider)
            
            configs = query.all()
            
            statuses = []
            for config in configs:
                cycle_start, cycle_end = BudgetService.get_current_billing_cycle(config.invoice_day)
                current_spending = BudgetService.get_current_spending(
                    config.provider,
                    config.invoice_day,
                    db
                )
                
                remaining = config.budget_amount_usd - current_spending
                percentage = (current_spending / config.budget_amount_usd * 100) if config.budget_amount_usd > 0 else 0
                
                statuses.append({
                    'provider': config.provider,
                    'budget_config_id': str(config.id),
                    'budget_amount_usd': config.budget_amount_usd,
                    'current_spending_usd': current_spending,
                    'remaining_budget_usd': remaining,
                    'percentage_used': round(percentage, 2),
                    'billing_cycle_start': cycle_start.isoformat(),
                    'billing_cycle_end': cycle_end.isoformat(),
                    'invoice_day': config.invoice_day,
                    'alert_thresholds': config.alert_thresholds,
                    'is_active': config.is_active
                })
            
            return {
                'statuses': statuses,
                'total_providers': len(statuses)
            }
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def check_budget_thresholds(
        provider: Optional[str] = None,
        db: Optional[Session] = None
    ) -> list:
        """Kiểm tra và trả về danh sách thresholds đã vượt quá.
        
        Args:
            provider: Provider name (tùy chọn). Nếu None, kiểm tra tất cả providers
            db: Database session (tùy chọn)
        
        Returns:
            list: Danh sách các thresholds đã vượt quá, mỗi item là dict:
                - budget_config: BudgetConfig instance
                - threshold_percentage: Ngưỡng đã vượt
                - current_spending: Chi phí hiện tại
                - cycle_start, cycle_end: Billing cycle dates
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Query active budget configs
            query = db.query(BudgetConfig).filter(BudgetConfig.is_active == True)
            if provider:
                query = query.filter(BudgetConfig.provider == provider)
            
            configs = query.all()
            exceeded_thresholds = []
            
            for config in configs:
                cycle_start, cycle_end = BudgetService.get_current_billing_cycle(config.invoice_day)
                current_spending = BudgetService.get_current_spending(
                    config.provider,
                    config.invoice_day,
                    db
                )
                
                percentage = (current_spending / config.budget_amount_usd * 100) if config.budget_amount_usd > 0 else 0
                
                # Kiểm tra từng threshold
                thresholds = config.alert_thresholds or []
                for threshold in thresholds:
                    if percentage >= threshold:
                        # Kiểm tra xem đã có alert cho threshold này chưa
                        from app.models import BudgetAlert
                        existing_alert = db.query(BudgetAlert).filter(
                            BudgetAlert.budget_config_id == config.id,
                            BudgetAlert.billing_cycle_start == cycle_start,
                            BudgetAlert.billing_cycle_end == cycle_end,
                            BudgetAlert.threshold_percentage == threshold,
                            BudgetAlert.acknowledged_at.is_(None)  # Chưa được acknowledge
                        ).first()
                        
                        # Chỉ thêm vào danh sách nếu chưa có alert chưa được acknowledge
                        if not existing_alert:
                            exceeded_thresholds.append({
                                'budget_config': config,
                                'threshold_percentage': threshold,
                                'current_spending': current_spending,
                                'budget_amount': config.budget_amount_usd,
                                'percentage_used': percentage,
                                'cycle_start': cycle_start,
                                'cycle_end': cycle_end,
                                'provider': config.provider
                            })
            
            return exceeded_thresholds
        finally:
            if should_close:
                db.close()
