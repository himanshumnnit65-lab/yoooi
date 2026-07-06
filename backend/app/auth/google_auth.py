"""
app/auth/google_auth.py
Google OAuth ID Token verification service
"""
from google.oauth2 import id_token
from google.auth.transport import requests
from typing import Optional, Dict, Any
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


def verify_google_id_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Google ID Token (JWT) sent from the client.
    
    Args:
        token: Google OAuth ID token (JWT)
        
    Returns:
        Dict containing user profile claims if valid, else None.
    """
    try:
        client_id = settings.google_client_id
        
        # Verify the ID Token against Google's public certificates
        # verify_oauth2_token accepts audience=client_id to verify the token is intended for this app
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            audience=client_id
        )
        
        # Verify issuer
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.warning("❌ Invalid token issuer")
            return None
            
        return {
            "user_id": id_info.get("sub"), # Unique Google ID
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
            "email_verified": id_info.get("email_verified", False)
        }
    except ValueError as e:
        logger.warning(f"❌ Failed to verify Google token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error during Google token verification: {e}", exc_info=True)
        return None
