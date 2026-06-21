import bcrypt
import jwt
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Union
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend import config

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify standard plain text password matches bcrypt hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Union[timedelta, None] = None) -> str:
    """Generate JWT access token with user details and roles."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token signature has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token credential.")

def get_current_user_from_credentials(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """FastAPI Dependency to retrieve the current user details from JWT."""
    token = credentials.credentials
    return decode_access_token(token)

def check_role(payload: Dict[str, Any], required_roles: list) -> bool:
    """Check if the token role matches any of the required roles."""
    user_role = payload.get("role")
    if user_role not in required_roles:
        raise HTTPException(status_code=403, detail="Permission denied. Insufficient role access.")
    return True

def validate_password_strength(password: str) -> None:
    """Enforce password strength policy (12+ chars, uppercase, lowercase, digit, special char)."""
    # Allow temp password during registration transition step
    if password == "TempPass_123456!":
        return
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters long.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character.")
