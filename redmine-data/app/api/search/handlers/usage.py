"""Handler các endpoint sử dụng LLM (hỗ trợ OpenAI, Google, Anthropic, Groq)"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.services.openai_usage_tracker import OpenAIUsageTracker

logger = logging.getLogger(__name__)


async def get_openai_usage(
    days: Optional[int] = 30,
    model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lấy thống kê sử dụng LLM API trong khoảng thời gian (hỗ trợ nhiều providers).
    
    Endpoint này trả về thống kê chi tiết về việc sử dụng LLM API:
    - Tổng số tokens (input, output, total)
    - Chi phí ước tính
    - Số lượng requests
    - Thống kê theo model (nếu có filter)
    
    Args:
        days: Số ngày gần đây để lấy thống kê (mặc định: 30)
        model: Tên model để filter (tùy chọn). Nếu None, lấy tất cả models
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa thống kê từ OpenAIUsageTracker.get_usage_stats():
            - total_input_tokens: Tổng số input tokens (int)
            - total_output_tokens: Tổng số output tokens (int)
            - total_tokens: Tổng số tokens (int)
            - estimated_cost: Chi phí ước tính (float)
            - request_count: Số lượng requests (int)
            - stats_by_model: Thống kê theo từng model (Dict, nếu không filter model)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình lấy thống kê
    
    Note:
        - Thống kê được tính từ start_date đến end_date (hiện tại)
        - Chi phí được tính dựa trên pricing của từng model
        - Nếu model được chỉ định, chỉ trả về thống kê cho model đó
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = OpenAIUsageTracker.get_usage_stats(
            start_date=start_date,
            end_date=end_date,
            model=model,
            db=db
        )
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_billing_cycle_usage(
    invoice_day: Optional[int] = 1,
    num_cycles: Optional[int] = 12,
    model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lấy thống kê sử dụng LLM API được nhóm theo billing cycles (hỗ trợ nhiều providers).
    
    Endpoint này trả về thống kê sử dụng được nhóm theo các billing cycles
    (chu kỳ thanh toán). Mỗi cycle bắt đầu từ invoice_day của tháng.
    
    Args:
        invoice_day: Ngày trong tháng khi invoice được tạo (1-31, mặc định: 1).
                     Mỗi billing cycle bắt đầu từ ngày này
        num_cycles: Số lượng billing cycles gần đây để trả về (1-24, mặc định: 12)
        model: Tên model để filter (tùy chọn). Nếu None, lấy tất cả models
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa thống kê từ OpenAIUsageTracker.get_billing_cycle_stats():
            - cycles: Danh sách các billing cycles (List[Dict]):
                - cycle_start: Ngày bắt đầu cycle (str, ISO format)
                - cycle_end: Ngày kết thúc cycle (str, ISO format)
                - total_input_tokens: Tổng số input tokens trong cycle (int)
                - total_output_tokens: Tổng số output tokens trong cycle (int)
                - total_tokens: Tổng số tokens trong cycle (int)
                - estimated_cost: Chi phí ước tính trong cycle (float)
                - request_count: Số lượng requests trong cycle (int)
            - total_across_cycles: Tổng thống kê qua tất cả cycles (Dict)
    
    Raises:
        HTTPException:
            - HTTP 400 nếu invoice_day không trong khoảng 1-31
            - HTTP 400 nếu num_cycles không trong khoảng 1-24
            - HTTP 500 nếu có lỗi trong quá trình lấy thống kê
    
    Note:
        - Billing cycles được tính từ invoice_day của mỗi tháng
        - Cycles được sắp xếp theo thời gian giảm dần (mới nhất trước)
        - Mỗi cycle bao gồm từ invoice_day của tháng này đến invoice_day-1 của tháng sau
    """
    try:
        # Xác thực invoice_day
        if not (1 <= invoice_day <= 31):
            raise HTTPException(status_code=400, detail="invoice_day must be between 1 and 31")
        
        if not (1 <= num_cycles <= 24):
            raise HTTPException(status_code=400, detail="num_cycles must be between 1 and 24")
        
        stats = OpenAIUsageTracker.get_billing_cycle_stats(
            invoice_day=invoice_day,
            num_cycles=num_cycles,
            model=model,
            db=db
        )
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get billing cycle stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

