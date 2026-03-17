"""
Access logging middleware for FastAPI
Logs all HTTP requests with useful information
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with timing and status information."""
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and log access information.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            Response: The HTTP response
        """
        # Start timer
        start_time = time.time()
        
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        
        # Process request
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
            raise
        finally:
            # Calculate processing time
            process_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Log the access
            logger.info(
                f'{client_host} - "{request.method} {request.url.path}" '
                f'{status_code} - {process_time:.2f}ms'
            )
