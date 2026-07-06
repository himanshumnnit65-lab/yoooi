"""
app/auth/middleware.py
Middleware for Unified Authentication (API Key and Google OAuth)
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import logging

from app.auth.api_key_manager import APIKeyManager
from app.auth.google_auth import verify_google_id_token
from app.messaging.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate API keys and Google Auth tokens for protected routes.
    Keeps the class name APIKeyAuthMiddleware for backward compatibility in main.py.
    """
    
    # Routes that don't require authentication
    EXEMPT_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
        "/status",
        "/health",
    ]
    
    # Routes that require admin scope
    ADMIN_PATHS = [
        "/api/v1/keys",
    ]
    
    def __init__(self, app, enforce_auth: bool = True):
        super().__init__(app)
        self.enforce_auth = enforce_auth
        self.manager: APIKeyManager = None
    
    async def get_manager(self) -> APIKeyManager:
        """Lazy load API key manager"""
        if self.manager is None:
            redis_client = get_redis_client()
            if redis_client._client is None:
                await redis_client.connect()
            self.manager = APIKeyManager(redis_client)
        return self.manager
    
    def is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        for exempt_path in self.EXEMPT_PATHS:
            if path == exempt_path or path.startswith(exempt_path + "/"):
                return True
        return False
    
    def is_admin_path(self, path: str) -> bool:
        """Check if path requires admin permissions"""
        for admin_path in self.ADMIN_PATHS:
            if path == admin_path or path.startswith(admin_path + "/"):
                return True
        return False
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and validate API key or Google token"""
        
        # Skip authentication for exempt paths
        if self.is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Skip if authentication not enforced (development mode)
        if not self.enforce_auth:
            logger.debug(f"Auth disabled for: {request.url.path}")
            return await call_next(request)
        
        # Extract Google Token (Authorization header or query param for WebSockets)
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.query_params.get("token")
            
        # Extract API Key (X-API-Key header or query param)
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        
        # 1. Authenticate via Google ID Token if present
        if token:
            user_info = verify_google_id_token(token)
            if user_info:
                request.state.user = user_info
                # Attach mock scopes for path authorization
                request.state.api_key_metadata = None 
                
                logger.debug(
                    f"Authenticated via Google: {user_info['email']} for path: {request.url.path}"
                )
                
                # Check admin paths (Google authenticated users are not admin by default)
                if self.is_admin_path(request.url.path):
                    logger.warning(
                        f"Google user {user_info['email']} attempted admin route: {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": "Forbidden", "details": "Admin permissions required"}
                    )
                
                return await call_next(request)
            else:
                logger.warning(f"Invalid Google token attempt for: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Unauthorized", "details": "Invalid or expired Google Token"}
                )
                
        # 2. Authenticate via traditional API Key if present
        if api_key:
            try:
                manager = await self.get_manager()
                metadata = await manager.validate_api_key(api_key)
                
                if not metadata:
                    logger.warning(f"Invalid API key attempt for: {request.url.path}")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"error": "Unauthorized", "details": "Invalid or expired API key"}
                    )
                
                # Check admin permissions for admin paths
                if self.is_admin_path(request.url.path):
                    if "admin" not in metadata.scopes:
                        logger.warning(
                            f"Non-admin key attempted admin route: {request.url.path}, "
                            f"key_id: {metadata.key_id}"
                        )
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"error": "Forbidden", "details": "Admin permissions required"}
                        )
                
                # Attach metadata to request state for use in routes
                request.state.api_key_metadata = metadata
                request.state.user = None
                
                logger.debug(
                    f"Authenticated via API Key: {metadata.name} for path: {request.url.path}"
                )
                
                return await call_next(request)
                
            except Exception as e:
                logger.error(f"Error validating API key: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Internal Error", "details": "Internal authentication error"}
                )
                
        # If neither is provided
        logger.warning(f"Missing authentication credentials for: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication required",
                "details": "Provide X-API-Key header or Authorization: Bearer <token>."
            }
        )