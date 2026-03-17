"""Budget checker scheduler job.

Job này kiểm tra budget thresholds định kỳ và trigger alerts khi cần.
Chạy mỗi giờ để đảm bảo alerts được gửi kịp thời.
"""
import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.budget import BudgetService, AlertService

logger = logging.getLogger(__name__)


def check_budget_thresholds_job():
    """Job để kiểm tra budget thresholds và trigger alerts.
    
    Job này:
    1. Lấy tất cả active budget configs
    2. Kiểm tra thresholds cho từng config
    3. Trigger alerts cho các thresholds đã vượt quá
    4. Tránh duplicate alerts (chỉ alert một lần cho mỗi threshold trong mỗi billing cycle)
    """
    db = SessionLocal()
    try:
        logger.info("Starting budget threshold check...")
        
        # Kiểm tra thresholds cho tất cả providers
        exceeded_thresholds = BudgetService.check_budget_thresholds(db=db)
        
        if not exceeded_thresholds:
            logger.info("No budget thresholds exceeded")
            return
        
        logger.info(f"Found {len(exceeded_thresholds)} exceeded thresholds")
        
        # Trigger alerts cho từng threshold
        for threshold_data in exceeded_thresholds:
            try:
                AlertService.trigger_alert(
                    budget_config=threshold_data['budget_config'],
                    threshold_percentage=threshold_data['threshold_percentage'],
                    current_spending=threshold_data['current_spending'],
                    budget_amount=threshold_data['budget_amount'],
                    cycle_start=threshold_data['cycle_start'],
                    cycle_end=threshold_data['cycle_end'],
                    db=db
                )
                logger.info(
                    f"Triggered alert for {threshold_data['provider']} - "
                    f"{threshold_data['threshold_percentage']}% threshold"
                )
            except Exception as e:
                logger.error(
                    f"Failed to trigger alert for {threshold_data['provider']}: {e}",
                    exc_info=True
                )
        
        logger.info("Budget threshold check completed")
        
    except Exception as e:
        logger.error(f"Budget threshold check failed: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    # Test job locally
    check_budget_thresholds_job()
