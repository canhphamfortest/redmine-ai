"""Alert service để trigger và gửi alerts qua các kênh."""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import BudgetConfig, BudgetAlert, LLMConfig
from app.database import SessionLocal
from app.services.budget.email_service import EmailService

logger = logging.getLogger(__name__)


class AlertService:
    """Service để trigger và gửi budget alerts."""
    
    @staticmethod
    def trigger_alert(
        budget_config: BudgetConfig,
        threshold_percentage: int,
        current_spending: float,
        budget_amount: float,
        cycle_start: datetime,
        cycle_end: datetime,
        db: Optional[Session] = None
    ) -> BudgetAlert:
        """Trigger alert và gửi qua các kênh.
        
        Args:
            budget_config: BudgetConfig instance
            threshold_percentage: Ngưỡng đã vượt quá
            current_spending: Chi phí hiện tại
            budget_amount: Budget amount
            cycle_start: Ngày bắt đầu billing cycle
            cycle_end: Ngày kết thúc billing cycle
            db: Database session (tùy chọn)
        
        Returns:
            BudgetAlert: Alert instance đã được tạo
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Xác định alert type
            percentage = (current_spending / budget_amount * 100) if budget_amount > 0 else 0
            alert_type = "budget_exceeded" if percentage >= 100 else "threshold_reached"
            
            # Nếu threshold > 80%, chuyển sang sử dụng free AI config
            if threshold_percentage > 80:
                try:
                    # Reset tất cả configs về non-default
                    db.query(LLMConfig).update({LLMConfig.is_default: False})
                    
                    # Set free config làm default
                    free_config_id = '528c7382-c5c3-4385-85f9-9038d95e9d32'
                    free_config = db.query(LLMConfig).filter(LLMConfig.id == free_config_id).first()
                    if free_config:
                        free_config.is_default = True
                        logger.info(f"Switched to free AI config due to budget threshold > 80%")
                    else:
                        logger.warning(f"Free AI config with ID {free_config_id} not found")
                except Exception as e:
                    logger.error(f"Failed to switch to free AI config: {e}")
                    # Không raise exception để không làm fail alert trigger
            
            # Xác định channels để gửi
            channels = ["in_app"]  # Luôn gửi in-app
            
            # Gửi email nếu có cấu hình SMTP
            try:
                email_sent = AlertService.send_email_alert(
                    budget_config,
                    threshold_percentage,
                    current_spending,
                    budget_amount,
                    cycle_start,
                    cycle_end
                )
                if email_sent:
                    channels.append("email")
            except Exception as e:
                logger.warning(f"Failed to send email alert: {e}")
            
            # Tạo alert record
            alert = BudgetAlert(
                budget_config_id=budget_config.id,
                provider=budget_config.provider,
                billing_cycle_start=cycle_start,
                billing_cycle_end=cycle_end,
                threshold_percentage=threshold_percentage,
                current_spending_usd=current_spending,
                budget_amount_usd=budget_amount,
                alert_type=alert_type,
                alert_channels=channels,
                sent_at=datetime.now()
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            logger.info(
                f"Budget alert triggered: {budget_config.provider} - "
                f"{threshold_percentage}% threshold - ${current_spending:.2f} / ${budget_amount:.2f}"
            )
            
            return alert
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}", exc_info=True)
            if db:
                db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def send_in_app_alert(alert: BudgetAlert) -> bool:
        """Lưu alert vào database để hiển thị trong UI.
        
        Args:
            alert: BudgetAlert instance
        
        Returns:
            bool: True nếu thành công
        """
        # Alert đã được lưu trong trigger_alert(), không cần làm gì thêm
        return True
    
    @staticmethod
    def send_email_alert(
        budget_config: BudgetConfig,
        threshold_percentage: int,
        current_spending: float,
        budget_amount: float,
        cycle_start: datetime,
        cycle_end: datetime
    ) -> bool:
        """Gửi email alert.
        
        Args:
            budget_config: BudgetConfig instance
            threshold_percentage: Ngưỡng đã vượt quá
            current_spending: Chi phí hiện tại
            budget_amount: Budget amount
            cycle_start: Ngày bắt đầu billing cycle
            cycle_end: Ngày kết thúc billing cycle
        
        Returns:
            bool: True nếu gửi thành công
        """
        try:
            return EmailService.send_budget_alert(
                budget_config,
                threshold_percentage,
                current_spending,
                budget_amount,
                cycle_start,
                cycle_end
            )
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    @staticmethod
    def create_alert_record(
        alert_data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> BudgetAlert:
        """Tạo alert record trong database.
        
        Args:
            alert_data: Dictionary chứa alert data
            db: Database session (tùy chọn)
        
        Returns:
            BudgetAlert: Alert instance đã được tạo
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            alert = BudgetAlert(**alert_data)
            db.add(alert)
            db.commit()
            db.refresh(alert)
            return alert
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_unacknowledged_alerts(
        provider: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[BudgetAlert]:
        """Lấy danh sách alerts chưa được acknowledge.
        
        Args:
            provider: Provider name (tùy chọn)
            db: Database session (tùy chọn)
        
        Returns:
            List[BudgetAlert]: Danh sách alerts chưa acknowledge
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            query = db.query(BudgetAlert).filter(
                BudgetAlert.acknowledged_at.is_(None)
            )
            
            if provider:
                query = query.filter(BudgetAlert.provider == provider)
            
            return query.order_by(BudgetAlert.sent_at.desc()).all()
        finally:
            if should_close:
                db.close()
