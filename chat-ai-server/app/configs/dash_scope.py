from dotenv import load_dotenv
import os

load_dotenv()

class DashScopeConfig:
    """阿里云DashScope配置信息"""
    api_key = os.getenv("DASHSCOPE_API_KEY") # 配置在根目录下.env 文件或者 Pycharm 的环境变量里
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    model_name = "qwen3-max"
    max_tokens = 2000
    temperature = 0.7