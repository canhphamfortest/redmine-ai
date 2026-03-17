"""Tính toán thống kê cho LLM usage (hỗ trợ OpenAI, Google, Anthropic, Groq)"""
import logging
from typing import Dict, Any, Optional
from collections import namedtuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func, Integer, cast, Date
from dateutil.relativedelta import relativedelta
from calendar import monthrange

from app.models import OpenAIUsageLog, SearchLog
from app.database import SessionLocal

logger = logging.getLogger(__name__)


def calculate_percentiles(response_times: list) -> Dict[str, float]:
    """Tính toán percentiles cho response times.
    
    Hàm này tính các percentile (p50, p75, p90, p95, p99) từ danh sách response times
    để phân tích performance. Sử dụng numpy để tính toán chính xác.
    
    Args:
        response_times: Danh sách response times tính bằng milliseconds (List[int | float])
    
    Returns:
        Dict[str, float]: Dictionary chứa các giá trị percentile:
            - p50: Median (50th percentile) (float)
            - p75: 75th percentile (float)
            - p90: 90th percentile (float)
            - p95: 95th percentile (float)
            - p99: 99th percentile (float)
            Tất cả = 0 nếu danh sách rỗng
    
    Note:
        - Sử dụng numpy.percentile() để tính toán
        - Percentiles giúp hiểu distribution của response times
        - p95 và p99 thường được dùng để set SLA và alerting thresholds
    """
    import numpy as np
    
    if not response_times:
        return {
            "p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0
        }
    
    arr = np.array(response_times)
    return {
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99))
    }


def get_usage_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    model: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Lấy thống kê chi tiết về LLM usage trong khoảng thời gian (hỗ trợ nhiều providers).
    
    Hàm này query database để lấy thống kê tổng hợp về usage:
    - Tổng tokens, chi phí, requests
    - Phân tích theo ngày
    - Phân tích theo model
    - Response time statistics (AI API và Search API)
    - Percentiles cho response times
    
    Args:
        start_date: Ngày bắt đầu (tùy chọn). Nếu None, mặc định là 30 ngày trước
        end_date: Ngày kết thúc (tùy chọn). Nếu None, mặc định là bây giờ
        model: Tên model để filter (tùy chọn). Nếu None, lấy tất cả models
        db: Database session (tùy chọn). Nếu None, tạo session mới
    
    Returns:
        Dict[str, Any]: Dictionary chứa thống kê chi tiết:
            - period: {start_date, end_date} (Dict)
            - total: Tổng thống kê (tokens, cost, requests, cached_requests, avg_response_time) (Dict)
            - response_time_stats: Thống kê response time (Dict):
                - ai_api: Stats cho AI API (count, avg, min, max, percentiles, raw_times) (Dict)
                - search_api: Stats cho Search API (count, avg, min, max, percentiles, raw_times) (Dict)
                - daily_breakdown: Response time theo ngày (List[Dict])
            - daily_breakdown: Thống kê theo ngày (tokens, cost, requests) (List[Dict])
            - model_breakdown: Thống kê theo model (tokens, cost, requests) (List[Dict])
    
    Note:
        - Response time stats chỉ tính cho non-cached requests
        - Raw times được giới hạn 500 giá trị cuối cùng cho biểu đồ
        - Percentiles được tính từ tất cả response times trong period
        - Session được tự động đóng nếu được tạo trong hàm
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        # Mặc định là 30 ngày gần nhất
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Query cơ bản
        query = db.query(
            func.sum(OpenAIUsageLog.input_token).label('total_input_tokens'),
            func.sum(OpenAIUsageLog.output_token).label('total_output_tokens'),
            func.sum(OpenAIUsageLog.total_tokens).label('total_tokens'),
            func.sum(OpenAIUsageLog.cost_usd).label('total_cost'),
            func.count(OpenAIUsageLog.id).label('total_requests'),
            func.sum(func.cast(OpenAIUsageLog.cached, Integer)).label('cached_requests'),
            func.avg(OpenAIUsageLog.response_time_ms).label('avg_response_time_ms')
        ).filter(
            OpenAIUsageLog.created_at >= start_date,
            OpenAIUsageLog.created_at <= end_date
        )
        
        # Lọc theo model nếu được cung cấp
        if model:
            query = query.filter(OpenAIUsageLog.model == model)
        
        result = query.first()
        
        # Phân tích theo ngày
        daily_query = db.query(
            cast(OpenAIUsageLog.created_at, Date).label('date'),
            func.sum(OpenAIUsageLog.total_tokens).label('tokens'),
            func.sum(OpenAIUsageLog.cost_usd).label('cost'),
            func.count(OpenAIUsageLog.id).label('requests')
        ).filter(
            OpenAIUsageLog.created_at >= start_date,
            OpenAIUsageLog.created_at <= end_date
        )
        
        if model:
            daily_query = daily_query.filter(OpenAIUsageLog.model == model)
        
        daily_stats = daily_query.group_by(
            cast(OpenAIUsageLog.created_at, Date)
        ).order_by(
            cast(OpenAIUsageLog.created_at, Date)
        ).all()
        
        # Phân tích theo model
        model_query = db.query(
            OpenAIUsageLog.model,
            func.sum(OpenAIUsageLog.total_tokens).label('tokens'),
            func.sum(OpenAIUsageLog.cost_usd).label('cost'),
            func.count(OpenAIUsageLog.id).label('requests')
        ).filter(
            OpenAIUsageLog.created_at >= start_date,
            OpenAIUsageLog.created_at <= end_date
        )
        
        if model:
            model_query = model_query.filter(OpenAIUsageLog.model == model)
        
        model_stats = model_query.group_by(
            OpenAIUsageLog.model
        ).all()
        
        # ===== THỐNG KÊ RESPONSE TIME (loại trừ cached) =====
        # Lấy tất cả response times không cached để tính percentiles
        non_cached_ai_times = db.query(OpenAIUsageLog.response_time_ms).filter(
            OpenAIUsageLog.created_at >= start_date,
            OpenAIUsageLog.created_at <= end_date,
            OpenAIUsageLog.cached == False,
            OpenAIUsageLog.response_time_ms.isnot(None)
        )
        if model:
            non_cached_ai_times = non_cached_ai_times.filter(OpenAIUsageLog.model == model)
        
        ai_times_list = [r[0] for r in non_cached_ai_times.all() if r[0] is not None]
        
        # Tính thống kê AI response time (chỉ non-cached)
        ai_time_stats = db.query(
            func.count(OpenAIUsageLog.id).label('count'),
            func.avg(OpenAIUsageLog.response_time_ms).label('avg'),
            func.min(OpenAIUsageLog.response_time_ms).label('min'),
            func.max(OpenAIUsageLog.response_time_ms).label('max')
        ).filter(
            OpenAIUsageLog.created_at >= start_date,
            OpenAIUsageLog.created_at <= end_date,
            OpenAIUsageLog.cached == False,
            OpenAIUsageLog.response_time_ms.isnot(None)
        )
        if model:
            ai_time_stats = ai_time_stats.filter(OpenAIUsageLog.model == model)
        ai_time_result = ai_time_stats.first()
        
        # Tính AI percentiles
        ai_percentiles = calculate_percentiles(ai_times_list)
        
        # Lấy Search API response times từ SearchLog
        # Tính search time = response_time_ms - generation_time_ms (nếu có)
        # Để loại bỏ thời gian AI call khỏi thời gian vector search
        search_logs = db.query(
            SearchLog.response_time_ms,
            SearchLog.generation_time_ms
        ).filter(
            SearchLog.created_at >= start_date,
            SearchLog.created_at <= end_date,
            SearchLog.response_time_ms.isnot(None)
        ).all()
        
        # Tính search time đã điều chỉnh (trừ generation_time_ms nếu có)
        # Nếu generation_time_ms không có giá trị (NULL) thì gán = 0 để phép trừ không lỗi
        search_times_list = []
        for log in search_logs:
            response_time = log.response_time_ms
            # Nếu generation_time_ms là None/NULL thì gán = 0, ngược lại dùng giá trị thực
            generation_time = log.generation_time_ms if log.generation_time_ms is not None else 0
            # Search time = tổng thời gian - thời gian AI generation
            search_time = response_time - generation_time
            # Đảm bảo không có giá trị âm
            if search_time > 0:
                search_times_list.append(search_time)
        
        # Tính thống kê Search response time từ danh sách đã điều chỉnh
        SearchTimeStats = namedtuple('SearchTimeStats', ['count', 'avg', 'min', 'max'])
        
        if search_times_list:
            search_time_stats = SearchTimeStats(
                count=len(search_times_list),
                avg=sum(search_times_list) / len(search_times_list),
                min=min(search_times_list),
                max=max(search_times_list)
            )
        else:
            search_time_stats = SearchTimeStats(
                count=0,
                avg=0,
                min=0,
                max=0
            )
        
        # Tính Search percentiles
        search_percentiles = calculate_percentiles(search_times_list)
        
        # Phân tích response time theo ngày (chỉ AI non-cached)
        daily_response_times = db.query(
            cast(OpenAIUsageLog.created_at, Date).label('date'),
            func.avg(OpenAIUsageLog.response_time_ms).label('avg_time'),
            func.min(OpenAIUsageLog.response_time_ms).label('min_time'),
            func.max(OpenAIUsageLog.response_time_ms).label('max_time'),
            func.count(OpenAIUsageLog.id).label('count')
        ).filter(
            OpenAIUsageLog.created_at >= start_date,
            OpenAIUsageLog.created_at <= end_date,
            OpenAIUsageLog.cached == False,
            OpenAIUsageLog.response_time_ms.isnot(None)
        )
        if model:
            daily_response_times = daily_response_times.filter(OpenAIUsageLog.model == model)
        
        daily_rt_stats = daily_response_times.group_by(
            cast(OpenAIUsageLog.created_at, Date)
        ).order_by(
            cast(OpenAIUsageLog.created_at, Date)
        ).all()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total": {
                "input_token": int(result.total_input_tokens or 0),
                "output_token": int(result.total_output_tokens or 0),
                "total_tokens": int(result.total_tokens or 0),
                "cost_usd": float(result.total_cost or 0.0),
                "requests": int(result.total_requests or 0),
                "cached_requests": int(result.cached_requests or 0),
                "avg_response_time_ms": float(result.avg_response_time_ms or 0)
            },
            "response_time_stats": {
                "ai_api": {
                    "count": int(ai_time_result.count or 0),
                    "avg_ms": float(ai_time_result.avg or 0),
                    "min_ms": float(ai_time_result.min or 0) if ai_time_result.min else 0,
                    "max_ms": float(ai_time_result.max or 0) if ai_time_result.max else 0,
                    "percentiles": ai_percentiles,
                    "raw_times": ai_times_list[-500:] if len(ai_times_list) > 500 else ai_times_list  # 500 giá trị cuối cho biểu đồ
                },
                "search_api": {
                    "count": int(search_time_stats.count or 0),
                    "avg_ms": float(search_time_stats.avg or 0),
                    "min_ms": float(search_time_stats.min or 0) if search_time_stats.min else 0,
                    "max_ms": float(search_time_stats.max or 0) if search_time_stats.max else 0,
                    "percentiles": search_percentiles,
                    "raw_times": search_times_list[-500:] if len(search_times_list) > 500 else search_times_list  # 500 giá trị cuối cho biểu đồ
                },
                "daily_breakdown": [
                    {
                        "date": str(daily.date),
                        "avg_ms": float(daily.avg_time or 0),
                        "min_ms": float(daily.min_time or 0),
                        "max_ms": float(daily.max_time or 0),
                        "count": int(daily.count or 0)
                    }
                    for daily in daily_rt_stats
                ]
            },
            "daily_breakdown": [
                {
                    "date": str(daily.date),
                    "tokens": int(daily.tokens or 0),
                    "cost_usd": float(daily.cost or 0.0),
                    "requests": int(daily.requests or 0)
                }
                for daily in daily_stats
            ],
            "model_breakdown": [
                {
                    "model": model_stat.model,
                    "tokens": int(model_stat.tokens or 0),
                    "cost_usd": float(model_stat.cost or 0.0),
                    "requests": int(model_stat.requests or 0)
                }
                for model_stat in model_stats
            ]
        }
    finally:
        if should_close:
            db.close()


def get_billing_cycle_stats(
    invoice_day: int = 1,
    num_cycles: int = 12,
    model: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Lấy thống kê usage được nhóm theo billing cycles (hỗ trợ nhiều providers).
    
    Hàm này tính toán các billing cycles (chu kỳ thanh toán hàng tháng) và
    tổng hợp usage cho mỗi cycle. Mỗi cycle bắt đầu từ invoice_day của tháng.
    
    Args:
        invoice_day: Ngày trong tháng khi invoice được tạo (1-31, mặc định: 1).
                    Mỗi billing cycle bắt đầu từ ngày này
        num_cycles: Số lượng billing cycles gần đây để trả về (mặc định: 12)
        model: Tên model để filter (tùy chọn). Nếu None, lấy tất cả models
        db: Database session (tùy chọn). Nếu None, tạo session mới
    
    Returns:
        Dict[str, Any]: Dictionary chứa:
            - invoice_day: Ngày invoice đã sử dụng (int)
            - cycles: Danh sách billing cycles (List[Dict]):
                - cycle_start: Ngày bắt đầu cycle (str, ISO format)
                - cycle_end: Ngày kết thúc cycle (str, ISO format)
                - cycle_label: Label của cycle (str, format: "YYYY-MM")
                - input_token: Tổng input tokens trong cycle (int)
                - output_token: Tổng output tokens trong cycle (int)
                - total_tokens: Tổng tokens trong cycle (int)
                - cost_usd: Tổng chi phí trong cycle (float)
                - requests: Số lượng requests trong cycle (int)
                - cached_requests: Số lượng cached requests trong cycle (int)
    
    Note:
        - Cycles được tính từ invoice_day của mỗi tháng
        - Xử lý các tháng có số ngày khác nhau (ví dụ: 31/1 -> 28/2)
        - Cycles được sắp xếp theo thời gian (cũ nhất trước)
        - Session được tự động đóng nếu được tạo trong hàm
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        # Tính toán billing cycles
        now = datetime.now()
        cycles = []
        
        # Bắt đầu từ ngày invoice của tháng hiện tại
        current_year = now.year
        current_month = now.month
        
        # Lấy ngày invoice cho tháng hiện tại
        # Nếu hôm nay trước ngày invoice, sử dụng ngày invoice của tháng trước
        if now.day < invoice_day:
            # Sử dụng ngày invoice của tháng trước
            last_month = now - relativedelta(months=1)
            cycle_start = datetime(last_month.year, last_month.month, invoice_day)
        else:
            # Sử dụng ngày invoice của tháng này
            cycle_start = datetime(current_year, current_month, invoice_day)
        
        # Tạo cycles
        for i in range(num_cycles):
            # Tính cycle end (ngày invoice của tháng tiếp theo)
            cycle_end = cycle_start + relativedelta(months=1)
            
            # Điều chỉnh nếu ngày invoice không tồn tại trong tháng tiếp theo (vd: 31/1 -> 28/2)
            if cycle_end.day != invoice_day:
                # Lấy ngày cuối cùng của tháng
                last_day = monthrange(cycle_end.year, cycle_end.month)[1]
                if invoice_day > last_day:
                    cycle_end = datetime(cycle_end.year, cycle_end.month, last_day)
                else:
                    cycle_end = datetime(cycle_end.year, cycle_end.month, invoice_day)
            
            cycles.append({
                'cycle_start': cycle_start,
                'cycle_end': cycle_end,
                'cycle_label': cycle_start.strftime('%Y-%m')
            })
            
            # Chuyển sang cycle trước
            cycle_start = cycle_start - relativedelta(months=1)
            # Điều chỉnh nếu ngày invoice không tồn tại trong tháng trước
            if cycle_start.day != invoice_day:
                last_day = monthrange(cycle_start.year, cycle_start.month)[1]
                if invoice_day > last_day:
                    cycle_start = datetime(cycle_start.year, cycle_start.month, last_day)
                else:
                    cycle_start = datetime(cycle_start.year, cycle_start.month, invoice_day)
        
        # Đảo ngược để có thứ tự thời gian (cũ nhất trước)
        cycles.reverse()
        
        # Query stats cho mỗi cycle
        cycle_stats = []
        for cycle in cycles:
            cycle_start = cycle['cycle_start']
            cycle_end = cycle['cycle_end']
            
            # Query cơ bản
            query = db.query(
                func.sum(OpenAIUsageLog.input_token).label('total_input_tokens'),
                func.sum(OpenAIUsageLog.output_token).label('total_output_tokens'),
                func.sum(OpenAIUsageLog.total_tokens).label('total_tokens'),
                func.sum(OpenAIUsageLog.cost_usd).label('total_cost'),
                func.count(OpenAIUsageLog.id).label('total_requests'),
                func.sum(func.cast(OpenAIUsageLog.cached, Integer)).label('cached_requests')
            ).filter(
                OpenAIUsageLog.created_at >= cycle_start,
                OpenAIUsageLog.created_at < cycle_end
            )
            
            # Lọc theo model nếu được cung cấp
            if model:
                query = query.filter(OpenAIUsageLog.model == model)
            
            result = query.first()
            
            cycle_stats.append({
                'cycle_start': cycle_start.isoformat(),
                'cycle_end': cycle_end.isoformat(),
                'cycle_label': cycle['cycle_label'],
                'input_token': int(result.total_input_tokens or 0),
                'output_token': int(result.total_output_tokens or 0),
                'total_tokens': int(result.total_tokens or 0),
                'cost_usd': float(result.total_cost or 0.0),
                'requests': int(result.total_requests or 0),
                'cached_requests': int(result.cached_requests or 0)
            })
        
        return {
            'invoice_day': invoice_day,
            'cycles': cycle_stats
        }
    finally:
        if should_close:
            db.close()

