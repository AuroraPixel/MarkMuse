"""
API 配置管理模块
集中管理所有第三方 API 的配置
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API 配置数据类"""
    # Mistral 配置
    mistral_api_key: Optional[str] = None
    
    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model_name: str = "gpt-4o"
    
    # 百度千帆配置
    qianfan_ak: Optional[str] = None
    qianfan_sk: Optional[str] = None
    
    # S3/MinIO 配置
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_endpoint_url: Optional[str] = None
    s3_path_prefix: str = ""
    
    # 并行处理配置
    parallel_images: int = 3
    
    # 数据库配置
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[str] = None
    db_name: Optional[str] = None
    database_url: Optional[str] = None


def load_api_config() -> APIConfig:
    """
    从环境变量加载 API 配置
    
    返回:
    - APIConfig: API 配置对象
    """
    # 加载 .env 文件
    load_dotenv()
    
    # 创建配置对象
    config = APIConfig(
        # Mistral 配置
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        
        # OpenAI 配置
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        openai_model_name=os.getenv("MODEL_NAME", "gpt-4o"),
        
        # 百度千帆配置
        qianfan_ak=os.getenv("QIANFAN_AK"),
        qianfan_sk=os.getenv("QIANFAN_SK"),
        
        # S3/MinIO 配置
        s3_access_key=os.getenv("S3_ACCESS_KEY"),
        s3_secret_key=os.getenv("S3_SECRET_KEY"),
        s3_bucket=os.getenv("S3_BUCKET"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        s3_path_prefix=os.getenv("S3_PATH_PREFIX", ""),
        
        # 并行处理配置
        parallel_images=int(os.getenv("PARALLEL_IMAGES", "3")),
        
        # 数据库配置
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=os.getenv("DB_PORT", "5432"),
        db_name=os.getenv("DB_NAME"),
        database_url=os.getenv("DATABASE_URL")
    )
    
    # 验证必要的配置
    if not config.mistral_api_key:
        logger.warning("未设置 MISTRAL_API_KEY 环境变量，部分功能将不可用")
    
    return config 

# 全局 API 配置实例
api_config = load_api_config()

# 数据库配置
# 如果直接提供了 DATABASE_URL，则使用它；否则从单独的配置构建
if api_config.database_url:
    DATABASE_URL = api_config.database_url
else:
    # 如果没有提供 DATABASE_URL，尝试从各部分构建
    if all([api_config.db_user, api_config.db_password, api_config.db_host, api_config.db_port, api_config.db_name]):
        DATABASE_URL = f"postgresql://{api_config.db_user}:{api_config.db_password}@{api_config.db_host}:{api_config.db_port}/{api_config.db_name}"
    else:
        DATABASE_URL = None
        logger.warning("数据库连接未完全配置，数据库功能将不可用。请配置 DATABASE_URL 或所有单独的数据库参数")

# 创建 SQLAlchemy 引擎和会话（如果DATABASE_URL可用）
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    engine = None
    SessionLocal = None
    Base = None

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖函数
    
    返回:
    - Generator[Session, None, None]: 数据库会话生成器
    """
    if SessionLocal is None:
        raise RuntimeError("数据库配置不完整，无法建立连接")
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 