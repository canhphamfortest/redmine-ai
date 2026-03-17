"""Google Gemini provider implementation using the new google-genai SDK."""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.config import settings
from app.services.llm_provider.base import LLMProvider

logger = logging.getLogger(__name__)

# Lazy import genai sau khi set environment variables
genai_client = None


class GoogleProvider(LLMProvider):
    provider_name = "google"

    def __init__(self, model: str, api_key: str = None, base_url: str = None, 
                 service_account_path: str = None):
        """
        Initialize Google Gemini provider using Service Account authentication.
        
        Args:
            model: Model name (e.g., "gemini-2.5-flash")
            api_key: Deprecated, not used. Kept for compatibility with base class.
            base_url: Base URL (optional)
            service_account_path: Path to service account JSON file
        
        Priority: service_account_path parameter > settings.google_service_account_path > GOOGLE_APPLICATION_CREDENTIALS env var
        """
        global genai_client
        
        super().__init__(model=model, api_key=None, base_url=base_url)
        
        # Configure SSL verification
        ssl_verify = getattr(settings, 'google_ssl_verify', True)
        
        # Determine service account file location
        # Priority: parameter > settings > environment variable
        service_account_file = None
        
        if service_account_path:
            service_account_file = service_account_path
        elif settings.google_service_account_path:
            service_account_file = settings.google_service_account_path
        elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            service_account_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not service_account_file:
            raise ValueError(
                "Google Gemini Service Account not configured. "
                "Please set GOOGLE_SERVICE_ACCOUNT_PATH or GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )
        
        # Validate service account file exists
        sa_path = Path(service_account_file)
        if not sa_path.exists():
            raise ValueError(f"Service account file not found: {service_account_file}")
        
        # Set GOOGLE_APPLICATION_CREDENTIALS for Application Default Credentials
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(sa_path.absolute())
        
        # Extract project ID from service account JSON if not configured
        project_id = settings.google_cloud_project
        if not project_id:
            try:
                import json
                with open(sa_path, 'r') as f:
                    sa_data = json.load(f)
                    project_id = sa_data.get('project_id', '')
                    if project_id:
                        logger.info(f"Extracted project_id from service account JSON: {project_id}")
            except Exception as e:
                logger.warning(f"Could not extract project_id from service account JSON: {e}")
        
        # Set project and location if configured
        if project_id:
            os.environ['GOOGLE_CLOUD_PROJECT'] = project_id
        if settings.google_cloud_location:
            os.environ['GOOGLE_CLOUD_LOCATION'] = settings.google_cloud_location
        
        location = settings.google_cloud_location or "us-central1"
        
        logger.info(f"Using Service Account authentication: {service_account_file}")
        logger.info(f"GOOGLE_CLOUD_PROJECT: {project_id or 'not set'}")
        logger.info(f"GOOGLE_CLOUD_LOCATION: {location}")
        
        # Clear API key environment variable if set (legacy)
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        
        # Disable SSL verification nếu được cấu hình
        # SDK mới sử dụng httpx, nhưng Google auth libraries sử dụng requests/urllib3
        if not ssl_verify:
            logger.warning("SSL verification is disabled for Google API. This is not recommended for production.")
            
            import ssl
            import urllib3
            import warnings
            
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            
            # Set environment variables
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            
            # Create a single unverified SSL context to reuse
            unverified_ssl_context = ssl.create_default_context()
            unverified_ssl_context.check_hostname = False
            unverified_ssl_context.verify_mode = ssl.CERT_NONE
            
            # 1. Patch requests (used by Google auth libraries)
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.ssl_ import create_urllib3_context
                
                class NoSSLAdapter(HTTPAdapter):
                    def init_poolmanager(self, *args, **kwargs):
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        kwargs['ssl_context'] = context
                        return super().init_poolmanager(*args, **kwargs)
                
                # Patch Session to always use NoSSLAdapter for HTTPS
                original_session_init = requests.Session.__init__
                def patched_session_init(self, *args, **kwargs):
                    original_session_init(self, *args, **kwargs)
                    self.mount('https://', NoSSLAdapter())
                requests.Session.__init__ = patched_session_init
                
                logger.info("✓ Patched requests to disable SSL verification")
            except Exception as e:
                logger.warning(f"Could not patch requests: {e}")
            
            # 2. Patch httpx (used by google-genai SDK)
            try:
                import httpx
                
                original_client_init = httpx.Client.__init__
                def patched_client_init(self, *args, **kwargs):
                    kwargs['verify'] = False
                    return original_client_init(self, *args, **kwargs)
                httpx.Client.__init__ = patched_client_init
                
                original_async_init = httpx.AsyncClient.__init__
                def patched_async_init(self, *args, **kwargs):
                    kwargs['verify'] = False
                    return original_async_init(self, *args, **kwargs)
                httpx.AsyncClient.__init__ = patched_async_init
                
                logger.info("✓ Patched httpx to disable SSL verification")
            except Exception as e:
                logger.warning(f"Could not patch httpx: {e}")
            
            # 3. Patch urllib3 at PoolManager level (most important)
            try:
                from urllib3.poolmanager import PoolManager
                
                original_poolmanager_init = PoolManager.__init__
                def patched_poolmanager_init(self, *args, **kwargs):
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    kwargs['ssl_context'] = context
                    kwargs['cert_reqs'] = ssl.CERT_NONE
                    return original_poolmanager_init(self, *args, **kwargs)
                PoolManager.__init__ = patched_poolmanager_init
                
                logger.info("✓ Patched urllib3 PoolManager to disable SSL verification")
            except Exception as e:
                logger.warning(f"Could not patch urllib3: {e}")
            
            logger.info("SSL verification disabled for all HTTP libraries")
        
        # Import SDK mới google-genai (REST API, không dùng gRPC)
        logger.info(f"Initializing Google Generative AI with model: {self.model}")
        if genai_client is None:
            logger.info("Importing google.genai module (new SDK)...")
            try:
                from google import genai
                
                # Validate required parameters for Vertex AI
                if not project_id:
                    raise ValueError(
                        "Google Cloud Project ID is required. "
                        "Set GOOGLE_CLOUD_PROJECT environment variable or ensure service account JSON contains 'project_id'."
                    )
                
                # Initialize Vertex AI client with explicit parameters
                logger.info(f"Initializing Vertex AI client with project={project_id}, location={location}")
                genai_client = genai.Client(
                    vertexai=True,
                    project=project_id,
                    location=location
                )
                logger.info("Successfully initialized google.genai Client with Vertex AI")
            except ImportError:
                logger.error("Failed to import google.genai. Please install: pip install google-genai")
                raise ValueError("google-genai SDK not installed. Please run: pip install google-genai")
            except Exception as e:
                logger.error(f"Failed to initialize Google Generative AI client: {e}", exc_info=True)
                # Provide helpful error message for common service account issues
                if "Could not automatically determine credentials" in str(e):
                    logger.error(
                        "Service account authentication failed. "
                        "Please verify GOOGLE_APPLICATION_CREDENTIALS points to a valid JSON file."
                    )
                raise
        
        self._client = genai_client
        self._model = self.model

    def get_client(self):
        return self._client

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        try:
            logger.info(f"Calling Google Gemini generate_content with prompt length: {len(prompt)}")
            logger.debug(f"Prompt preview: {prompt[:200]}...")
            
            # Gọi generate_content với timeout sử dụng ThreadPoolExecutor
            def _generate_content():
                logger.info("Inside _generate_content function, about to call generate_content...")
                try:
                    # SDK mới sử dụng: client.models.generate_content(model="...", contents="...")
                    logger.info(f"Calling client.models.generate_content with model: {self._model}")
                    response = self._client.models.generate_content(
                        model=self._model,
                        contents=prompt
                    )
                    logger.info("generate_content call completed successfully")
                    return response
                except Exception as inner_e:
                    logger.error(f"Exception inside _generate_content: {inner_e}", exc_info=True)
                    raise
            
            logger.info("Submitting generate_content to ThreadPoolExecutor...")
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_generate_content)
                    logger.info("Waiting for generate_content result with 60s timeout...")
                    response = future.result(timeout=60)  # Timeout 60 giây
                    logger.info("Received response from generate_content")
            except FutureTimeoutError:
                logger.error("Google Gemini API call timed out after 60 seconds")
                return "Xin lỗi, đã xảy ra lỗi timeout khi kết nối với AI model (Gemini). Vui lòng thử lại sau.", {}
            except Exception as e:
                logger.error(f"Error in Google Gemini API call: {e}", exc_info=True)
                raise
            
            logger.info("Successfully received response from Google Gemini")
            
            # Extract text từ response
            # SDK mới: response.text
            text = response.text if hasattr(response, "text") else ""
            
            # Extract usage info từ response
            # SDK mới có thể có usage_metadata hoặc usage
            usage_info = {
                "input_token": 0,
                "output_token": 0,
                "total_tokens": 0,
            }
            
            # Thử extract usage từ các thuộc tính có thể có
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                # Lấy input_token từ prompt_token_count của Google API
                input_token = getattr(usage, "prompt_token_count", 0) or 0
                output_token = getattr(usage, "candidates_token_count", 0) or 0
                total_tokens = getattr(usage, "total_token_count", 0) or 0
                
                # Tính prompt_token = max(0, total_tokens - output_token)
                prompt_token = max(0, total_tokens - output_token)
                
                usage_info["input_token"] = input_token
                usage_info["output_token"] = output_token
                usage_info["total_tokens"] = total_tokens
                usage_info["prompt_token"] = prompt_token
            elif hasattr(response, "usage"):
                usage = response.usage
                # Lấy input_token từ prompt_tokens (OpenAI-compatible format)
                input_token = getattr(usage, "prompt_tokens", 0) or 0
                output_token = getattr(usage, "completion_tokens", 0) or 0
                total_tokens = getattr(usage, "total_tokens", 0) or 0
                
                # Tính prompt_token = max(0, total_tokens - output_token)
                prompt_token = max(0, total_tokens - output_token)
                
                usage_info["input_token"] = input_token
                usage_info["output_token"] = output_token
                usage_info["total_tokens"] = total_tokens
                usage_info["prompt_token"] = prompt_token
            
            if text:
                logger.info(f"Google Gemini returned response with {usage_info.get('total_tokens', 0)} tokens")
                return text, usage_info
            else:
                logger.error("Google Gemini returned empty response")
                return "Xin lỗi, không nhận được phản hồi từ AI model.", usage_info
        except Exception as e:
            logger.error(f"Google Gemini generation failed: {e}", exc_info=True)
            return "Xin lỗi, đã xảy ra lỗi khi kết nối với AI model (Gemini).", {}
