"""Service LLM Config chính (hỗ trợ OpenAI, Google, Anthropic, Groq)"""
import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import LLMConfig
from app.config import settings
from app.services.openai_usage_tracker import OpenAIUsageTracker
from app.services.openai_config_service.queries import (
    get_all_configs,
    get_active_configs,
    get_config_by_model
)

logger = logging.getLogger(__name__)


class LLMConfigService:
    """Service quản lý cấu hình pricing và model mặc định cho nhiều LLM providers."""
    
    @staticmethod
    def get_all_configs(db: Session = None, provider: str = None):
        """Lấy tất cả config OpenAI từ database.
        
        Args:
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới
        
        Returns:
            List[OpenAIConfig]: Danh sách tất cả configs, bao gồm cả inactive
        """
        return get_all_configs(db=db, provider=provider)
    
    @staticmethod
    def get_active_configs(db: Session = None, provider: str = None):
        """Lấy tất cả config OpenAI đang active.
        
        Args:
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới
        
        Returns:
            List[OpenAIConfig]: Danh sách configs có is_active=True
        """
        return get_active_configs(db=db, provider=provider)
    
    @staticmethod
    def get_config_by_model(model_name: str, db: Session = None, provider: str = None) -> Optional[LLMConfig]:
        """Lấy config cho một model cụ thể.
        
        Args:
            model_name: Tên model cần lấy config (string)
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới
        
        Returns:
            OpenAIConfig | None: Config object nếu tìm thấy, None nếu không
        """
        return get_config_by_model(model_name, db=db, provider=provider)
    
    @staticmethod
    def get_default_model(db: Session = None) -> Optional[str]:
        """Lấy tên model mặc định (provider mặc định). Giữ tương thích ngược."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            default_config = db.query(LLMConfig).filter(
                LLMConfig.is_default == True,
                LLMConfig.is_active == True
            ).first()
            
            if default_config:
                return default_config.model_name
            
            return None
        except Exception as e:
            logger.warning(f"Failed to get default model from DB: {e}")
            return None
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_default_provider_and_model(db: Session = None) -> Optional[Dict[str, str]]:
        """Trả về provider + model mặc định từ DB, fallback config settings."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        try:
            default_config = db.query(LLMConfig).filter(
                LLMConfig.is_default == True,
                LLMConfig.is_active == True
            ).first()
            if default_config:
                return {
                    "provider": default_config.provider or "openai",
                    "model": default_config.model_name,
                    "api_key": default_config.api_key,
                    "base_url": default_config.base_url,
                }
            
            # Fallback về settings - lấy API key và model từ settings dựa trên provider
            provider = settings.default_llm_provider or "openai"
            api_key = None
            model = settings.openai_model  # Default model
            
            # Lấy API key và model từ settings dựa trên provider
            if provider == "google":
                # Google Gemini chỉ sử dụng Service Account, không cần API key
                api_key = None
                model = getattr(settings, 'google_model', None) or "gemini-1.5-pro"  # Default Google model
            elif provider == "anthropic":
                api_key = settings.anthropic_api_key
                model = getattr(settings, 'anthropic_model', None) or "claude-3-sonnet-20240229"
            elif provider == "groq":
                api_key = settings.groq_api_key
                model = getattr(settings, 'groq_model', None) or "llama-3.3-70b-versatile"
            elif provider == "openai":
                api_key = settings.openai_api_key
                model = settings.openai_model
            
            return {
                "provider": provider,
                "model": model,
                "api_key": api_key,
                "base_url": None,
            }
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def set_default_model(model_name: str, db: Session = None, provider: str = "openai") -> bool:
        """Đặt một model làm mặc định (bỏ tất cả các model khác).
        
        Hàm này:
        1. Kiểm tra model có tồn tại trong database không
        2. Bỏ tất cả các default flags khác
        3. Đặt model này làm default và active
        
        Args:
            model_name: Tên model để đặt làm mặc định (string)
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới và commit
        
        Returns:
            bool: True nếu thành công, False nếu không tìm thấy model
        
        Note:
            - Chỉ có một model có thể là default tại một thời điểm
            - Model được đặt làm default cũng được đảm bảo is_active=True
            - Session được tự động commit và đóng nếu được tạo trong hàm
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Kiểm tra model có tồn tại không
            config = db.query(LLMConfig).filter(LLMConfig.model_name == model_name).first()
            if not config:
                return False
            
            # Bỏ tất cả các default khác
            db.query(LLMConfig).filter(LLMConfig.is_default == True).update({
                LLMConfig.is_default: False
            })
            
            # Đặt model này làm mặc định
            config.is_default = True
            config.is_active = True  # Đảm bảo nó đang active
            config.provider = provider or config.provider
            
            if should_close:
                db.commit()
            else:
                db.flush()
            
            return True
        except Exception as e:
            if should_close:
                db.rollback()
            logger.error(f"Failed to set default model: {e}", exc_info=True)
            return False
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_pricing_for_model(model_name: str, provider: str = "openai", use_db: bool = True):
        """Lấy pricing cho một model theo provider, ưu tiên DB rồi fallback mặc định.
        
        Args:
            model_name: Tên model cần lấy pricing (string)
            use_db: Có kiểm tra database trước không (mặc định: True)
        
        Returns:
            Dict[str, float]: Dictionary chứa:
                - input: Giá input tokens cho mỗi 1M tokens (float)
                - output: Giá output tokens cho mỗi 1M tokens (float)
        
        Note:
            - Nếu use_db=True, kiểm tra database trước
            - Fallback về hardcoded pricing nếu không tìm thấy trong DB
        """
        from app.services.openai_config_service.pricing import get_pricing_for_model as _get_pricing
        return _get_pricing(model_name, provider=provider, use_db=use_db)
    
    @staticmethod
    def create_or_update_config(
        model_name: str,
        input_price_per_1m: float,
        output_price_per_1m: float,
        is_active: bool = True,
        description: Optional[str] = None,
        db: Session = None,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> LLMConfig:
        """Tạo hoặc cập nhật config LLM (đa provider).
        
        Hàm này tạo config mới nếu chưa tồn tại, hoặc cập nhật config hiện có
        nếu đã tồn tại (dựa trên model_name).
        
        Args:
            model_name: Tên model (string)
            input_price_per_1m: Giá input tokens cho mỗi 1M tokens (float)
            output_price_per_1m: Giá output tokens cho mỗi 1M tokens (float)
            is_active: Trạng thái active (mặc định: True)
            description: Mô tả config (tùy chọn)
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới và commit
        
        Returns:
            OpenAIConfig: Config object đã được tạo hoặc cập nhật
        
        Raises:
            Exception: Nếu có lỗi trong quá trình tạo/cập nhật
        
        Note:
            - Nếu config đã tồn tại, chỉ cập nhật các trường được cung cấp
            - Description chỉ được cập nhật nếu được cung cấp (không None)
            - Session được tự động commit và đóng nếu được tạo trong hàm
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Kiểm tra config có tồn tại không
            config = db.query(LLMConfig).filter(LLMConfig.model_name == model_name).first()
            
            if config:
                # Cập nhật config hiện có
                config.input_price_per_1m = input_price_per_1m
                config.output_price_per_1m = output_price_per_1m
                config.is_active = is_active
                config.provider = provider or config.provider
                config.api_key = api_key if api_key is not None else config.api_key
                config.base_url = base_url if base_url is not None else config.base_url
                if description is not None:
                    config.description = description
            else:
                # Tạo mới
                config = LLMConfig(
                    provider=provider or "openai",
                    model_name=model_name,
                    input_price_per_1m=input_price_per_1m,
                    output_price_per_1m=output_price_per_1m,
                    is_active=is_active,
                    description=description,
                    api_key=api_key,
                    base_url=base_url,
                )
                db.add(config)
            
            if should_close:
                db.commit()
            
            db.flush()
            return config
        except Exception as e:
            if should_close:
                db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def delete_config(model_name: str, db: Session = None) -> bool:
        """Xóa config OpenAI khỏi database.
        
        Args:
            model_name: Tên model cần xóa config (string)
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới và commit
        
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy config
        
        Raises:
            Exception: Nếu có lỗi trong quá trình xóa
        
        Note:
            - Session được tự động commit và đóng nếu được tạo trong hàm
            - Không thể undo sau khi xóa
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            config = db.query(LLMConfig).filter(LLMConfig.model_name == model_name).first()
            if config:
                db.delete(config)
                if should_close:
                    db.commit()
                db.flush()
                return True
            return False
        except Exception as e:
            if should_close:
                db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def sync_default_pricing(db: Session = None, set_default_model: str = None) -> int:
        """Đồng bộ pricing mặc định từ OpenAIUsageTracker.PRICING sang database.
        
        Hàm này đồng bộ tất cả pricing từ hardcoded PRICING dictionary vào database.
        Mỗi model trong PRICING sẽ được tạo hoặc cập nhật trong database.
        
        Args:
            db: Database session (tùy chọn). Nếu None, sẽ tạo session mới và commit
            set_default_model: Tên model để đặt làm mặc định (tùy chọn, mặc định: 'gpt-4o-mini').
                              Chỉ đặt làm default nếu chưa có default nào khác
        
        Returns:
            int: Số lượng config đã tạo/cập nhật
        
        Raises:
            Exception: Nếu có lỗi trong quá trình sync
        
        Note:
            - Tất cả models trong PRICING được sync với is_active=True
            - Model được chỉ định làm default (nếu chưa có default khác)
            - Session được tự động commit và đóng nếu được tạo trong hàm
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            count = 0
            default_model = set_default_model or 'gpt-4o-mini'
            default_provider = settings.default_llm_provider or "openai"
            
            for provider_name, provider_pricing in OpenAIUsageTracker.PRICING.items():
                for model_name, pricing in provider_pricing.items():
                    is_default = (model_name == default_model and provider_name == default_provider)
                    
                    config = LLMConfigService.create_or_update_config(
                        model_name=model_name,
                        input_price_per_1m=pricing["input"],
                        output_price_per_1m=pricing["output"],
                        is_active=True,
                        description=f"Pricing mặc định cho {provider_name}:{model_name}",
                        db=db,
                        provider=provider_name,
                    )
                    
                    if is_default:
                        existing_default = db.query(LLMConfig).filter(
                            LLMConfig.is_default == True,
                            LLMConfig.model_name != model_name
                        ).first()
                        
                        if not existing_default:
                            db.query(LLMConfig).filter(
                                LLMConfig.is_default == True,
                                LLMConfig.model_name != model_name
                            ).update({LLMConfig.is_default: False})
                            config.is_default = True
                
                    count += 1
            
            if should_close:
                db.commit()
            
            return count
        except Exception as e:
            if should_close:
                db.rollback()
            raise
        finally:
            if should_close:
                db.close()


# Backward compatibility alias
OpenAIConfigService = LLMConfigService
