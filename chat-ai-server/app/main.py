"""应用启动类"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import user_router, chat_router

# 创建FastAPI应用实例
app = FastAPI(title="聊天机器人", version="1.0.0", description="基于fastapi+VUE的聊天机器人")

# 添加CORS中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加相关路由模块
# prefix: 为该路由模块添加URL前缀，如下所有用户相关路由都会以/user开头
# tags: 在API文档中用于分组显示，便于组织和查看
app.include_router(user_router.router, prefix="/user", tags=["用户管理"])
app.include_router(chat_router.router, prefix="/chat", tags=["聊天管理"])



# ==================== 应用启动配置 ====================

if __name__ == "__main__":
    import uvicorn

    # 打印启动信息
    print("=" * 50)
    print("聊天机器人服务启动中...")
    print("=" * 50)
    print("Web界面: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("=" * 50)

    # 启动服务器
    uvicorn.run(
        "main:app",  # 应用模块路径
        host="0.0.0.0",  # 监听所有网络接口
        port=8000,  # 端口号
        reload=True,  # 开发模式热重载
        log_level="debug"  # 日志级别
    )
