"""聊天相关的数据模型"""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.configs.dash_scope import DashScopeConfig


config = DashScopeConfig()

class ChatMessage(BaseModel):
    """
    聊天消息数据模型
    用于表示对话中的单条消息，包含角色、内容和时间戳
    Fields：
        role：消息角色: user(用户), assistant(AI助手), system(系统)
    """
    role: str
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """
    客户端聊天请求数据模型
    定义了客户端发送聊天请求时需要包含的所有参数

    Fields：
        messages：对话历史消息列表，包含用户和助手的所有消息
        model：要使用的AI模型名称，默认使用配置中的模型
        temperature：温度值(千问：0-2)，控制回答的随机性
        max_tokens：最大生成token数，限制回答长度
        stream：是否启用流式输出，默认 False
    """
    messages: List[ChatMessage]
    model: Optional[str] = config.model_name
    temperature: Optional[float] = config.temperature
    max_tokens: Optional[int] = config.max_tokens
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    """
    服务端聊天响应数据模型（非流式）
    请求的响应包含完整的AI回答和使用统计

    Fields：
        message：AI助手的回复消息
        model：使用的模型名称
        usage：token使用情况统计
    """
    message: ChatMessage
    model: str
    usage: Optional[Dict[str, Any]] = None


class StreamResponse(BaseModel):
    """
    流式响应数据模型
    用于流式输出时的每个数据块，支持Server-Sent Events (SSE)

    Fields：
        content：本次返回的内容片段
        finished：是否为最后一个片段，True表示流式响应结束
        model：使用的模型名称
        timestamp：当前片段的时间戳
    """
    content: str
    finished: bool
    model: str
    timestamp: datetime

