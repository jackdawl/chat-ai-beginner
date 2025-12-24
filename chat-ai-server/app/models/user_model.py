"""用户相关的模型"""
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    """用户登录输入的模型"""
    username: str
    password: str


class Token(BaseModel):
    """
    访问令牌响应模型
    用于登录成功后返回JWT令牌
    access_token: JWT访问令牌
    token_type: 令牌类型，通常是"bearer"
    """
    message: str
    access_token: str
    token_type: str
    username: str


class TokenData(BaseModel):
    """
    令牌数据模型
    用于解析JWT令牌中的用户信息
    """
    username: Optional[str] = None


class User(BaseModel):
    """
    用户基础信息模型
    定义用户的公开信息（不包含密码等敏感信息）
    """
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    """
    数据库中的用户模型
    继承User模型，添加了密码哈希字段
    """
    hashed_password: str


class UserSignUp(BaseModel):
    """
    用户注册请求模型，接收前端传来的数据
    """
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    """
    用户更新请求模型，接收前端传来的数据
    """
    email: Optional[str] = None
    full_name: Optional[str] = None