"""
任务队列API主模块
提供基于FastAPI的任务队列Web API
"""

import logging
import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from clients.db.database import init_db
from config.api_config import get_db
from .routes import router as tasks_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# 创建应用
app = FastAPI(
    title="任务队列API",
    description="基于Celery的通用任务队列Web API，支持任务提交和查询",
    version="1.0.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应设置为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"内部服务器错误: {str(exc)}"}
    )

# 健康检查端点
@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "healthy"}

# 数据库检查端点
@app.get("/db-check", tags=["健康检查"])
async def db_check(db: Session = Depends(get_db)):
    try:
        # 执行简单查询
        db.execute("SELECT 1").scalar()
        return {"status": "database connected"}
    except Exception as e:
        logger.error(f"数据库连接检查失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "database error", "detail": str(e)}
        )

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    # 初始化数据库
    try:
        init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
    
    # 日志启动信息
    logger.info("任务队列API启动成功")

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("任务队列API关闭")

# 添加路由
app.include_router(tasks_router)

# 主入口
if __name__ == "__main__":
    import uvicorn
    # 获取端口配置
    port = int(os.environ.get("PORT", 8000))
    
    # 启动服务器
    uvicorn.run(
        "task_api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    ) 