"""用户路由配置"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


from app.models.user_model import *
from app.dao.user_dao import UserDAO
from app.utils import pwd_util, jwt_util

# =====================================================
# 依赖实例
# =====================================================

# 创建路由器实例
# 这个路由器将包含所有用户相关的路由
router = APIRouter()
# 创建用户DB连接实例
user_dao = UserDAO()

# OAuth2密码Bearer令牌方案
# tokenUrl: 获取token的端点URL，必须与实际的token端点路径匹配
# 这告诉FastAPI和前端客户端在哪里获取访问令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token", scheme_name="JWT_Bearer")
router.swagger_ui_init_oauth = {
    "clientId": "test-client-id",
    "usePkceWithAuthorizationCodeGrant": True,
    "scopes": {
        "items.read": "Read access to protected resources",
        "items.write": "Write access to protected resources"
    }
}

# =====================================================
# 依赖函数
# =====================================================

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    验证用户身份

    Args:
        username (str): 用户名
        password (str): 明文密码

    Returns:
        Optional[UserInDB]: 验证成功返回用户对象，失败返回False
    """
    # 首先获取用户信息
    user = user_dao.get_user(username)
    if not user:
        return False

    # 验证密码是否正确
    if not pwd_util.verify_password(password, user.hashed_password):
        return False

    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    """
    从JWT令牌中获取当前用户信息
    这是一个依赖函数，会被其他需要用户身份验证的路由使用

    Args:
        token (str): 从请求头中提取的Bearer令牌

    Returns:
        UserInDB: 当前用户信息

    Raises:
        HTTPException: 如果令牌无效或用户不存在
    """
    # 定义认证异常，当令牌验证失败时抛出
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 验证失败", 
        headers={"WWW-Authenticate": "Bearer"}, 
    )

    try:
        # 解码JWT令牌
        payload = jwt_util.decode_token(token)

        # 从令牌中提取用户名（sub是JWT标准字段，表示subject/主题）
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # 创建令牌数据对象
        token_data = TokenData(username=username)

    except jwt.PyJWTError:
        # JWT解码失败（令牌无效、过期等）
        raise credentials_exception

    # 从数据库中获取用户信息
    user = user_dao.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    获取当前活跃用户
    这是另一个依赖函数，确保用户不仅通过了身份验证，而且账户是活跃的

    Args:
        current_user (User): 从get_current_user依赖中获取的当前用户

    Returns:
        User: 活跃的用户信息

    Raises:
        HTTPException: 如果用户账户被禁用
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="无效用户")
    return current_user



# =====================================================
# API路由端点
# =====================================================

@router.post("/signup", response_model=User, summary="用户注册", description="创建用户账户")
async def sign_up(user: UserSignUp) -> User:
    """
    用户注册端点
    创建新的用户账户，密码会被自动哈希加密存储

    Args:
        user (SignInRequest): 包含用户注册信息的对象

    Returns:
        User: 创建成功的用户信息（不包含密码）

    Raises:
        HTTPException: 如果用户名已存在
    """
    # 检查用户名是否已经存在
    db_user = user_dao.get_user(user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"  
        )

    # 对密码进行哈希加密
    hashed_password = pwd_util.get_password_hash(user.password)

    # 创建用户数据字典
    user_dict = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "disabled": False  # 新用户默认为启用状态
    }

    # 将用户数据保存到"数据库"
    new_user = UserInDB.model_validate(user_dict)
    user_dao.save_user(new_user)

    # 返回用户信息（不包含密码哈希）
    return User(**user_dict)



@router.post("/token", response_model=Token, summary="用户登录", description="使用用户名和密码获取JWT访问令牌")
async def login_for_access_token(login_data: LoginRequest) -> Token:
    """
    用户登录端点
    接受用户名和密码，返回JWT访问令牌

    Args:
        login_data : 包含用户名和密码

    Returns:
        Token: 包含访问令牌和令牌类型的对象

    Raises:
        HTTPException: 如果用户名或密码不正确
    """
    # 验证用户身份
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        # 认证失败，返回401未授权状态码
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",  # 用户名或密码错误
            headers={"WWW-Authenticate": "Bearer"},
        )


    # 创建访问令牌，将用户名作为subject存储在令牌中
    access_token = jwt_util.create_access_token(
        data={"sub": user.username},
    )

    token_dict = {
        "message": "登录成功",
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }

    # 返回令牌和令牌类型
    return Token.model_validate(token_dict)


@router.post("/logout", summary="用户退出", description="用户退出登录")
async def logout(
        current_user: Annotated[User, Depends(get_current_active_user)] # 依赖函数必须在引用路由上面
) -> dict:
    """
    用户退出登录端点
    由于JWT是无状态的，服务端不需要做特殊处理
    主要是返回成功消息，让前端清除本地存储的token

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 退出成功的消息
    """
    return {
        "message": "退出登录成功",
        "username": current_user.username,
        "logout_time": datetime.now(timezone.utc).isoformat()
    }


@router.get("/get", response_model=User, summary="获取用户信息", description="获取当前登录用户的个人信息")
async def get_user_info(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    获取当前用户信息端点
    需要有效的JWT令牌才能访问

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        User: 当前用户的信息
    """
    return current_user



@router.put("/update", response_model=User, summary="更新用户信息", description="更新当前登录用户的个人信息")
async def update_user_info(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    更新当前用户信息端点
    允许用户更新自己的邮箱和全名

    Args:
        user_update (UserUpdate): 包含要更新的用户信息
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        User: 更新后的用户信息
    """
    current_user.email = user_update.email
    current_user.full_name = user_update.full_name
    # 获取并返回更新后的用户信息
    updated_user = user_dao.update_user(current_user)
    return updated_user


@router.delete("/del", summary="删除用户账户", description="删除当前登录用户的账户")
async def delete_user_account(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    删除当前用户账户端点
    允许用户删除自己的账户

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 删除成功的确认消息

    Raises:
        HTTPException: 如果用户不存在（理论上不会发生）
    """
    user_dao.delete_user(current_user.username)
    return {
        "message": "用户删除成功",
        "deleted_user": current_user.username,
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }



@router.get("/all", summary="获取所有用户", description="获取系统中所有用户的列表（需要管理员权限）")
async def get_all_users(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    获取所有用户列表端点
    返回系统中所有用户的信息（不包含密码）
    实际应用中通过角色控制权限

    Args:
        current_user (User): 通过依赖注入获取的当前用户信息

    Returns:
        dict: 包含用户列表和总数的字典
    """
    users = []
    user_dict = user_dao.list_user()
    for username, user_data in user_dict.items():
        # 创建User对象（不包含密码哈希）
        user_info = {k: v for k, v in user_data.items() if k != 'hashed_password'}
        users.append(User(**user_info))

    return {
        "data": users,
        "total": len(users)
    }
