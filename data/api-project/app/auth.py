"""认证模块"""

import hashlib
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key"
security = HTTPBearer()


def hash_password(password: str) -> str:
    """加密密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed_password


def create_token(user_id: int) -> str:
    """创建JWT Token"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """验证Token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")


def get_current_user(user_id: int = Depends(verify_token)) -> dict:
    """获取当前用户"""
    from .database import get_user
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
