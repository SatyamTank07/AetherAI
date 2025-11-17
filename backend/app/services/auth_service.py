# services/auth_service.py
import jwt
from jwt import PyJWTError as JWTError
from fastapi import HTTPException, status
from typing import Dict
import requests
import datetime
from scripts.helper.logConfig import get_logger
from scripts.config import load_config


logger = get_logger("AuthService")

class AuthService:
    def __init__(self):
        config = load_config()
        self.secret_key = config.get("JWT_SECRET_KEY")
        self.algorithm = config.get("JWT_ALGORITHM", "HS256")
        self.token_expiry = config.get("JWT_EXPIRY_MINUTES", 30)
        self.google_client_id = config.get("GOOGLE_CLIENT_ID")
        self.google_client_secret = config.get("GOOGLE_CLIENT_SECRET")
        self.google_redirect_uri = config.get("GOOGLE_REDIRECT_URI")
        
    def create_access_token(self, user_id: str) -> str:
        """Generate a JWT for the user."""
        expire = datetime.utcnow() + datetime.timedelta(minutes=self.token_expiry)
        to_encode = {"sub": user_id, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Generated access token for user: {user_id}")
        return encoded_jwt
    def verify_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: user_id not found"
                )
            return user_id
        except JWTError as e:
            logger.error(f"Error verifying token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def get_google_login_url(self) -> str:
        """Generate Google OAuth login URL."""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"

    async def validate_google_code(self, code: str) -> Dict:
        """Exchange Google authorization code for tokens and validate ID token."""
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.google_redirect_uri,
            "grant_type": "authorization_code"
        }
        try:
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            id_token = token_data.get("id_token")
            if not id_token:
                raise HTTPException(status_code=400, detail="No ID token received from Google")

            # Verify ID token
            user_info = jwt.decode(id_token, options={"verify_signature": False})  # Google's public keys can be used for verification
            if user_info.get("aud") != self.google_client_id:
                raise HTTPException(status_code=400, detail="Invalid Google token audience")
            return {
                "google_id": user_info.get("sub"),
                "email": user_info.get("email"),
                "username": user_info.get("name")
            }
        except requests.RequestException as e:
            logger.error(f"Error exchanging Google code: {e}")
            raise HTTPException(status_code=400, detail="Failed to validate Google code")
