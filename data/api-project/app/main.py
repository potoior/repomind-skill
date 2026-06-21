"""用户管理API"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from .database import get_user, create_user, update_user, delete_user
from .auth import verify_token, hash_password

app = FastAPI(title="用户管理系统")


class UserCreate(BaseModel):
    """用户创建请求"""
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str


@app.get("/api/users", response_model=List[UserResponse])
async def list_users():
    """获取用户列表"""
    verify_token()
    users = get_user()
    return users


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user_detail(user_id: int):
    """获取用户详情"""
    verify_token()
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.post("/api/users", response_model=UserResponse)
async def create_new_user(user: UserCreate):
    """创建新用户"""
    verify_token()
    hashed_password = hash_password(user.password)
    new_user = create_user(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    return new_user


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_existing_user(user_id: int, user: UserCreate):
    """更新用户信息"""
    verify_token()
    existing_user = get_user(user_id)
    if not existing_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    hashed_password = hash_password(user.password)
    updated_user = update_user(
        user_id=user_id,
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    return updated_user


@app.delete("/api/users/{user_id}")
async def delete_existing_user(user_id: int):
    """删除用户"""
    verify_token()
    existing_user = get_user(user_id)
    if not existing_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    delete_user(user_id)
    return {"message": "用户已删除"}


@app.post("/api/auth/login")
async def login(username: str, password: str):
    """用户登录"""
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token = create_token(user.id)
    return {"token": token}
