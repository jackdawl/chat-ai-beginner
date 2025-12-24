from datetime import datetime, timedelta, timezone

import jwt

from app.configs.jwt import JWTConfig

jwt_config = JWTConfig()

def create_access_token(data: dict) -> str:
    """
    创建JWT访问令牌

    Args:
        data (dict): 要编码到令牌中的数据（通常包含用户标识）

    Returns:
        str: 编码后的JWT令牌
    """
    # 复制数据以避免修改原始数据
    to_encode = data.copy()

    # 计算过期时间，没有设置过期时间，就默认设置15分钟
    expires_delta = timedelta(minutes=int(jwt_config.access_token_expire_minutes))
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    # 添加过期时间到令牌数据中
    to_encode.update({"exp": expire})

    # 使用密钥和算法对数据进行编码
    encoded_jwt = jwt.encode(to_encode, jwt_config.secret_key, algorithm=jwt_config.algorithm)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """
    解码JWT令牌

    Args:
        token (str): 要解码的JWT令牌

    Returns:
        str: 编码后的JWT令牌
    """
    payload = jwt.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
    return payload