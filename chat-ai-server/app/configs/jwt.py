from dotenv import load_dotenv
import os

load_dotenv()

class JWTConfig:
    """JWT配置信息"""
    secret_key: str = os.getenv("JWT_SECRET_KEY")
    algorithm: str = os.getenv("JWT_ALGORITHM")
    access_token_expire_minutes: int = 30