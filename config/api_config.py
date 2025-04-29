"""
API 配置管理模块
集中管理所有第三方 API 的配置
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

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
        parallel_images=int(os.getenv("PARALLEL_IMAGES", "3"))
    )
    
    # 验证必要的配置
    if not config.mistral_api_key:
        logger.warning("未设置 MISTRAL_API_KEY 环境变量，部分功能将不可用")
    
    return config 