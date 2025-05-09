"""
数据库连接和初始化
"""

import logging
from config.api_config import Base, engine, SessionLocal, get_db

logger = logging.getLogger(__name__)

__all__ = ["init_db", "Base", "engine", "SessionLocal", "get_db"]

def init_db():
    """
    初始化数据库
    创建所有在模型中定义的表
    """
    if engine is None:
        logger.error("数据库引擎未初始化，无法创建表")
        return False
    
    try:
        # 创建定义的所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
        return True
    except Exception as e:
        logger.error(f"创建数据库表时出错: {e}")
        return False 