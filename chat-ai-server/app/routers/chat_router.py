"""聊天路由配置"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from openai import OpenAI
from typing import Annotated

from app.models.chat_model import *
from app.models.user_model import User
from app.routers import user_router
import asyncio
import json

# =====================================================
# 依赖实例
# =====================================================

# 创建路由器实例
# 这个路由器将包含所有聊天相关的路由
router = APIRouter()
# 为路由器添加标签和元数据，用于API文档生成
# router.tags = ["聊天服务"]
# router.responses = {
#     401: {"description": "未授权 - 需要有效的JWT令牌"},
#     429: {"description": "请求过多 - 配额已用完"},
#     500: {"description": "服务器内部错误"}
# }

# 内存存储用户聊天历史
# 结构: {username: [ChatMessage, ChatMessage, ...]}
# 注意: 生产环境中应该使用数据库或中间件存储，如Redis
chatHistory = {}

# 创建OpenAI客户端实例
# 使用配置中的API密钥和基础URL
config = DashScopeConfig()
client = OpenAI(api_key=config.api_key, base_url=config.base_url)


# =====================================================
# 依赖函数
# =====================================================


def convert_messages_for_api(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    """
    将自定义的ChatMessage转换为OpenAI API需要的格式
    OpenAI API需要的消息格式是字典列表，每个字典包含role和content字段

    Args:
        messages (List[ChatMessage]): 自定义的消息对象列表

    Returns:
        List[Dict[str, str]]: OpenAI API格式的消息列表

    Example:
        输入: [ChatMessage(role="user", content="你好")]
        输出: [{"role": "user", "content": "你好"}]
    """
    return [{"role": msg.role, "content": msg.content} for msg in messages]


async def generate_stream_response(request: ChatRequest, username: str):
    """
    生成流式响应的异步生成器
    处理流式AI响应，将OpenAI的流式输出转换为SSE格式

    Args:
        request (ChatRequest): 聊天请求对象
        username (str): 当前用户名

    Yields:
        str: 格式化的SSE数据，每行以"data: "开头

    Note:
        使用Server-Sent Events (SSE) 协议进行实时数据传输
        客户端需要使用EventSource或类似技术接收流式数据
    """
    try:
        # 转换消息格式为OpenAI API需要的格式
        api_messages = convert_messages_for_api(request.messages)

        # 调用OpenAI流式API
        # stream=True 启用流式输出，API会返回一个迭代器
        stream = client.chat.completions.create(
            model=request.model or config.MODEL_NAME,  # 使用指定模型或默认模型
            messages=api_messages,  # 对话历史
            max_tokens=request.max_tokens,  # 最大token数
            temperature=request.temperature,  # 创造性温度
            stream=True,  # 启用流式输出
            stream_options={"include_usage": True} # 在最后一个 chunk 中展示总的 token 消耗
        )

        # 用于累积完整的回答内容
        accumulated_content = ""

        # 遍历流式响应的每个数据块
        for chunk in stream:
            # 检查数据块是否包含有效内容
            if chunk.choices and chunk.choices[0].delta.content:
                # 提取本次数据块的内容
                chunk_content = chunk.choices[0].delta.content

                # 累积到完整内容中
                accumulated_content += chunk_content

                # 构建流式响应数据对象
                response_data = StreamResponse(
                    content=chunk.choices[0].delta.content,  # 本次片段内容
                    finished=False,  # 标记为未完成
                    model=request.model or config.MODEL_NAME,  # 使用的模型
                    timestamp=datetime.now()  # 当前时间戳
                )

                # 格式化为SSE格式并发送
                # SSE格式: "data: {json_data}\n\n"
                yield f"data: {response_data.model_dump_json()}\n\n"

                # 异步让出控制权，避免阻塞事件循环
                # 这对于处理大量并发请求很重要
                await asyncio.sleep(0.01)

        # 流式响应结束后的处理
        if accumulated_content:
            # 构建结束信号响应
            final_response = StreamResponse(
                content='',  # 结束信号不包含内容
                finished=True,  # 标记为已完成
                model=request.model or config.MODEL_NAME,
                timestamp=datetime.now()
            )

            # 将完整的AI回复保存到用户的聊天历史中
            chatHistory[username].append(
                ChatMessage(
                    role="assistant",
                    content=accumulated_content,
                    timestamp=datetime.now()
                )
            )

            # 发送结束信号
            yield f"data: {final_response.model_dump_json()}\n\n"

    except Exception as e:
        # 流式响应过程中的错误处理
        # 构建错误响应并发送给客户端
        error_response = {
            "error": str(e),  # 错误信息
            "finished": True,  # 标记为结束
            "timestamp": datetime.now().isoformat()  # 错误发生时间
        }

        # 发送错误信息
        yield f"data: {json.dumps(error_response)}\n\n"


# =====================================================
# API路由端点定义
# =====================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        current_user: Annotated[User, Depends(user_router.get_current_active_user)]
):
    """
    聊天对话接口 - 需要登录认证

    这是核心的聊天接口，支持流式和非流式两种模式：
    - 非流式: 等待AI完整回答后一次性返回
    - 流式: 实时返回AI生成的内容片段

    安全特性:
    - 需要有效的JWT令牌
    - 自动配额检查和限制
    - 用户数据隔离

    Args:
        request (ChatRequest): 聊天请求数据
        current_user (User): 通过JWT认证获取的当前用户信息

    Returns:
        ChatResponse: 非流式模式的完整响应
        StreamingResponse: 流式模式的SSE响应

    Raises:
        HTTPException:
            - 429: 配额已用完
            - 500: AI模型调用失败或其他服务器错误
    """
    try:
        # 从认证信息中获取用户名，确保数据安全
        username = current_user.username

        # 初始化用户的聊天历史记录（如果不存在）
        if username not in chatHistory:
            chatHistory[username] = []

        # 将用户的最新消息添加到历史记录
        user_message = ChatMessage(
            role=request.messages[-1].role,
            content=request.messages[-1].content,
            timestamp=datetime.now()
        )
        chatHistory[username].append(user_message)

        # 根据请求类型处理：流式 vs 非流式
        if request.stream:
            # ===== 流式输出处理 =====

            # 返回流式响应
            # StreamingResponse 用于处理SSE协议
            return StreamingResponse(
                generate_stream_response(request, username),  # 异步生成器
                media_type="text/plain",  # 媒体类型
                headers={
                    "Cache-Control": "no-cache",  # 禁用缓存
                    "Connection": "keep-alive",  # 保持连接
                    "Content-Type": "text/event-stream",  # SSE内容类型
                }
            )

        else:
            # ===== 非流式输出处理 =====

            # 转换消息格式为OpenAI API需要的格式
            api_messages = convert_messages_for_api(request.messages)

            # 调用OpenAI API获取完整响应
            response = client.chat.completions.create(
                model=request.model or config.MODEL_NAME,
                messages=api_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False  # 非流式模式
            )

            # 检查API响应是否有效
            if response.choices and len(response.choices) > 0:
                # 构建AI助手的回复消息
                assistant_message = ChatMessage(
                    role="assistant",
                    content=response.choices[0].message.content or "",
                    timestamp=datetime.now()
                )

                # 将AI回复添加到用户的聊天历史
                chatHistory[username].append(assistant_message)

                # 构建完整的响应对象
                chat_response = ChatResponse(
                    message=assistant_message,  # AI回复消息
                    model=response.model,  # 实际使用的模型
                    usage=response.usage.model_dump() if response.usage else None,  # token使用统计
                )

                return chat_response
            else:
                # API返回空响应的错误处理
                raise HTTPException(
                    status_code=500,
                    detail="AI模型返回了空响应"
                )

    except HTTPException:
        # 重新抛出HTTP异常（如配额限制）
        raise
    except Exception as e:
        # 捕获所有其他异常并转换为HTTP异常
        error_message = f"处理聊天请求时发生错误: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/models")
async def get_models(
        current_user: Annotated[User, Depends(user_router.get_current_active_user)]
):
    """
    获取可用的AI模型列表 - 需要登录
    返回当前可用的AI模型列表，用户可以在聊天时选择使用

    Args:
        current_user (User): 通过JWT认证获取的当前用户信息

    Returns:
        dict: 包含模型列表和默认模型的字典

    Note:
        如果无法获取模型列表，会返回默认配置
    """
    try:
        # 尝试从OpenAI API获取可用模型列表
        models = client.models.list()

        return {
            "models": [model.id for model in models.data],  # 模型ID列表
            "default_model": config.MODEL_NAME,  # 默认模型
            "user": current_user.username  # 请求用户
        }
    except Exception as e:
        # 如果获取模型列表失败，返回默认配置
        return {
            "models": [config.MODEL_NAME],  # 只返回默认模型
            "default_model": config.MODEL_NAME,
            "note": "使用默认模型配置",  # 提示信息
            "user": current_user.username
        }


@router.get("/history")
async def get_user_history(
        current_user: Annotated[User, Depends(user_router.get_current_active_user)]
) -> List[ChatMessage]:
    """
    获取当前用户的聊天历史 - 安全版本
    只返回当前认证用户的聊天历史，确保数据隐私

    Args:
        current_user (User): 通过JWT认证获取的当前用户信息

    Returns:
        List[ChatMessage]: 用户的历史消息列表

    Security:
        用户只能访问自己的聊天历史，无法访问他人数据
    """
    username = current_user.username

    # 如果用户没有聊天历史，返回空列表
    if username not in chatHistory:
        return []

    # 返回用户的完整聊天历史
    # 创建新的ChatMessage对象确保数据一致性
    return [
        ChatMessage(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp
        )
        for msg in chatHistory[username]
    ]


@router.delete("/history")
async def clear_user_history(
        current_user: Annotated[User, Depends(user_router.get_current_active_user)]
):
    """
    清空当前用户的聊天历史
    删除用户的所有聊天记录，此操作不可逆

    Args:
        current_user (User): 通过JWT认证获取的当前用户信息

    Returns:
        dict: 操作确认信息

    Warning:
        此操作会永久删除用户的聊天历史，无法恢复
    """
    username = current_user.username

    # 如果用户有聊天历史，则删除
    if username in chatHistory:
        # 获取删除前的消息数量用于统计
        message_count = len(chatHistory[username])

        # 删除用户的聊天历史
        del chatHistory[username]

        return {
            "message": "聊天历史已清空",
            "user": username,
            "deleted_messages": message_count,  # 删除的消息数量
            "timestamp": datetime.now()
        }
    else:
        # 用户没有聊天历史
        return {
            "message": "用户没有聊天历史",
            "user": username,
            "deleted_messages": 0,
            "timestamp": datetime.now()
        }


@router.get("/health")
async def health_check():
    """
    健康检查接口 - 无需认证
    用于监控服务状态，通常被负载均衡器或监控系统调用

    Returns:
        dict: 服务状态信息

    Note:
        此接口不需要认证，可被任何人访问
    """
    return {
        "status": "healthy",  # 服务状态
        "timestamp": datetime.now(),  # 当前时间
        "version": "1.0.0",  # 服务版本
        "model": config.MODEL_NAME,  # 默认AI模型
    }



