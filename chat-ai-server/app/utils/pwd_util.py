from passlib.context import CryptContext
# 密码加密上下文配置
# schemes: 支持的密码哈希方案，bcrypt是目前推荐的安全哈希算法
# deprecated: 标记为已弃用的方案（用于向后兼容）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    生成密码的哈希值

    Args:
        password (str): 明文密码

    Returns:
        str: 密码的bcrypt哈希值
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否正确

    Args:
        plain_password (str): 用户输入的明文密码
        hashed_password (str): 数据库中存储的密码哈希

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)
