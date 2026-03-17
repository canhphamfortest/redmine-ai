"""Email service để gửi budget alerts."""
import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

from app.models import BudgetConfig

logger = logging.getLogger(__name__)


class EmailService:
    """Service để gửi email alerts."""
    
    @staticmethod
    def _get_smtp_config() -> Optional[dict]:
        """Lấy cấu hình SMTP từ environment variables.
        
        Returns:
            dict: SMTP config hoặc None nếu không có cấu hình
        """
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "")
        ses_configuration_set = os.getenv("SES_CONFIGURATION_SET", "")
        
        if not smtp_host or not smtp_user or not smtp_password:
            return None
        
        return {
            'host': smtp_host,
            'port': smtp_port,
            'user': smtp_user,
            'password': smtp_password,
            'use_tls': smtp_use_tls,
            'from_email': smtp_from_email or smtp_user,
            'ses_configuration_set': ses_configuration_set
        }
    
    @staticmethod
    def _get_recipients() -> list:
        """Lấy danh sách email recipients từ environment variable.
        
        Returns:
            list: Danh sách email addresses
        """
        recipients_str = os.getenv("BUDGET_ALERT_EMAIL_RECIPIENTS", "")
        if not recipients_str:
            return []
        
        # Split by comma và strip whitespace
        recipients = [email.strip() for email in recipients_str.split(",") if email.strip()]
        return recipients
    
    @staticmethod
    def _create_email_body(
        budget_config: BudgetConfig,
        threshold_percentage: int,
        current_spending: float,
        budget_amount: float,
        cycle_start: datetime,
        cycle_end: datetime
    ) -> str:
        """Tạo nội dung email.
        
        Args:
            budget_config: BudgetConfig instance
            threshold_percentage: Ngưỡng đã vượt quá
            current_spending: Chi phí hiện tại
            budget_amount: Budget amount
            cycle_start: Ngày bắt đầu billing cycle
            cycle_end: Ngày kết thúc billing cycle
        
        Returns:
            str: HTML email body
        """
        percentage = (current_spending / budget_amount * 100) if budget_amount > 0 else 0
        remaining = budget_amount - current_spending
        
        # Xác định màu sắc dựa trên threshold
        if percentage >= 100:
            color = "#dc3545"  # Red
            status = "EXCEEDED"
        elif percentage >= 80:
            color = "#ffc107"  # Yellow
            status = "WARNING"
        else:
            color = "#28a745"  # Green
            status = "ALERT"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f8f9fa; }}
                .metric {{ margin: 10px 0; padding: 10px; background-color: white; border-left: 4px solid {color}; }}
                .metric-label {{ font-weight: bold; color: #666; }}
                .metric-value {{ font-size: 24px; color: {color}; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Budget Alert: {status}</h1>
                    <p>Provider: {budget_config.provider.upper()}</p>
                </div>
                <div class="content">
                    <h2>Budget Threshold Reached</h2>
                    <p>Your LLM usage has reached <strong>{threshold_percentage}%</strong> of the budget limit.</p>
                    
                    <div class="metric">
                        <div class="metric-label">Current Spending</div>
                        <div class="metric-value">${current_spending:,.2f}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Budget Amount</div>
                        <div class="metric-value">${budget_amount:,.2f}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Remaining Budget</div>
                        <div class="metric-value">${remaining:,.2f}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Usage Percentage</div>
                        <div class="metric-value">{percentage:.2f}%</div>
                    </div>
                    
                    <h3>Billing Cycle</h3>
                    <p><strong>Start:</strong> {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>End:</strong> {cycle_end.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    
                    <p style="margin-top: 20px;">
                        <em>This is an automated alert from the RAG System Budget Monitor.</em>
                    </p>
                </div>
                <div class="footer">
                    <p>RAG System - Budget Alert System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    @staticmethod
    def send_budget_alert(
        budget_config: BudgetConfig,
        threshold_percentage: int,
        current_spending: float,
        budget_amount: float,
        cycle_start: datetime,
        cycle_end: datetime
    ) -> bool:
        """Gửi email alert về budget threshold.
        
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
        smtp_config = EmailService._get_smtp_config()
        if not smtp_config:
            logger.debug("SMTP not configured, skipping email alert")
            return False
        
        recipients = EmailService._get_recipients()
        if not recipients:
            logger.debug("No email recipients configured, skipping email alert")
            return False
        
        try:
            # Tạo email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Budget Alert: {budget_config.provider.upper()} - {threshold_percentage}% Threshold Reached"
            msg['From'] = smtp_config['from_email']
            msg['To'] = ", ".join(recipients)
            
            # Thêm AWS SES Configuration Set header nếu có
            if smtp_config['ses_configuration_set']:
                msg['X-SES-CONFIGURATION-SET'] = smtp_config['ses_configuration_set']
                logger.debug(f"Added SES Configuration Set: {smtp_config['ses_configuration_set']}")
            
            # Tạo HTML body
            html_body = EmailService._create_email_body(
                budget_config,
                threshold_percentage,
                current_spending,
                budget_amount,
                cycle_start,
                cycle_end
            )
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Gửi email qua SMTP (AWS SES)
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config['use_tls']:
                    server.starttls()
                server.login(smtp_config['user'], smtp_config['password'])
                server.send_message(msg)
            
            logger.info(f"Budget alert email sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send budget alert email: {e}", exc_info=True)
            return False
