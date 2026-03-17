"""Module OpenAI usage tracker.

Module này cung cấp các chức năng để track và thống kê việc sử dụng OpenAI API:
- OpenAIUsageTracker: Class chính để log usage và chi tiết
- Statistics: Tính toán thống kê usage theo thời gian và billing cycles
- Pricing: Tính toán chi phí dựa trên token usage và pricing configs

Các chức năng chính:
- Log usage: Ghi log mỗi lần gọi OpenAI API (tokens, cost, response time)
- Statistics: Thống kê tổng hợp usage, response times, percentiles
- Billing cycles: Thống kê theo chu kỳ thanh toán hàng tháng
- Pricing: Tính toán chi phí dựa trên model và token usage
"""
from app.services.openai_usage_tracker.tracker import OpenAIUsageTracker
from app.services.openai_usage_tracker.statistics import get_usage_stats, get_billing_cycle_stats
from app.services.openai_usage_tracker.pricing import calculate_cost, PRICING

# Thêm các static methods vào class để tương thích ngược
OpenAIUsageTracker.get_usage_stats = staticmethod(get_usage_stats)
OpenAIUsageTracker.get_billing_cycle_stats = staticmethod(get_billing_cycle_stats)
OpenAIUsageTracker.calculate_cost = staticmethod(calculate_cost)
OpenAIUsageTracker.PRICING = PRICING

__all__ = ['OpenAIUsageTracker']

