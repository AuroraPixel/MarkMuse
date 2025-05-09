"""
客户端工厂模块
提供创建各种客户端实例的工厂函数
"""

import logging
from typing import Optional, Dict, Any

from config import APIConfig
from clients.ocr import OCRClient, MistralOCRClient
from clients.storage import S3Storage
from clients.llm import LLMClient, OpenAILLMClient, QianfanLLMClient, LLMClientError
from clients.redis import RedisClient, RedisError
from clients.celery.app import celery_app, configure_celery

logger = logging.getLogger(__name__)


def create_ocr_client(config: APIConfig) -> Optional[OCRClient]:
    """
    创建 OCR 客户端
    
    参数:
    - config: API 配置
    
    返回:
    - OCRClient: OCR 客户端实例，如果创建失败则返回 None
    """
    if not config.mistral_api_key:
        logger.error("未设置 Mistral API 密钥，无法创建 OCR 客户端")
        return None
    
    try:
        return MistralOCRClient(api_key=config.mistral_api_key)
    except Exception as e:
        logger.error(f"创建 OCR 客户端失败: {str(e)}")
        return None


def create_storage_client(config: APIConfig, storage_type: str = "s3") -> Optional[S3Storage]:
    """
    创建存储客户端
    
    参数:
    - config: API 配置
    - storage_type: 存储类型，目前支持 's3'
    
    返回:
    - Storage: 存储客户端实例，如果创建失败则返回 None
    """
    try:
        if storage_type.lower() == "s3":
            # 检查必要的配置
            if not config.s3_access_key or not config.s3_secret_key or not config.s3_bucket:
                logger.warning("未设置完整的 S3 配置，无法创建存储客户端")
                return None
            
            return S3Storage(config)
        else:
            logger.error(f"不支持的存储类型: {storage_type}")
            return None
    except Exception as e:
        logger.error(f"创建存储客户端失败: {str(e)}")
        return None


def create_llm_client(config: APIConfig, provider: str = "openai") -> Optional[LLMClient]:
    """
    创建 LLM 客户端
    
    参数:
    - config: API 配置
    - provider: 提供商，支持 'openai' 和 'qianfan'
    
    返回:
    - LLMClient: LLM 客户端实例，如果创建失败则返回 None
    """
    try:
        if provider == "openai":
            if not config.openai_api_key:
                logger.warning("未设置 OpenAI API 密钥，无法创建 LLM 客户端")
                return None
            
            return OpenAILLMClient(
                api_key=config.openai_api_key,
                model_name=config.openai_model_name,
                base_url=config.openai_base_url
            )
        elif provider == "qianfan":
            if not config.qianfan_ak or not config.qianfan_sk:
                logger.warning("未设置百度千帆 AK/SK，无法创建 LLM 客户端")
                return None
            
            return QianfanLLMClient(
                ak=config.qianfan_ak,
                sk=config.qianfan_sk
            )
        else:
            logger.error(f"不支持的 LLM 客户端提供商: {provider}")
            return None
    except Exception as e:
        logger.error(f"创建 LLM 客户端失败: {str(e)}")
        return None


def create_redis_client(config: APIConfig) -> Optional[RedisClient]:
    """
    创建 Redis 客户端
    
    参数:
    - config: API 配置
    
    返回:
    - RedisClient: Redis 客户端实例，如果创建失败则返回 None
    """
    try:
        return RedisClient(config=config)
    except RedisError as e:
        logger.error(f"创建 Redis 客户端失败: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"创建 Redis 客户端时出现未知错误: {str(e)}")
        return None


def create_celery_app(config: APIConfig, **kwargs) -> Any:
    """
    配置并返回 Celery 应用实例
    
    参数:
    - config: API 配置
    - kwargs: 其他 Celery 配置参数
    
    返回:
    - Any: Celery 应用实例
    """
    try:
        return configure_celery(celery_app, config, **kwargs)
    except Exception as e:
        logger.error(f"配置 Celery 应用失败: {str(e)}")
        # 返回一个最小配置的Celery应用
        celery_app.conf.broker_url = 'redis://localhost:6379/0'
        celery_app.conf.result_backend = 'redis://localhost:6379/0'
        return celery_app


def create_clients(config: APIConfig, llm_provider: str = "openai") -> Dict[str, Any]:
    """
    创建所有客户端
    
    参数:
    - config: API 配置
    - llm_provider: LLM 提供商，支持 'openai' 和 'qianfan'
    
    返回:
    - Dict[str, Any]: 包含所有创建的客户端的字典
    """
    clients = {
        "ocr_client": create_ocr_client(config),
        "llm_client": create_llm_client(config, llm_provider),
        "storage_client": None,
        "redis_client": None,
        "celery_app": celery_app
    }
    
    # 尝试创建存储客户端
    if hasattr(config, 's3_access_key') and config.s3_access_key:
        clients["storage_client"] = create_storage_client(config)
    
    # 尝试创建Redis客户端
    try:
        clients["redis_client"] = create_redis_client(config)
    except Exception as e:
        logger.warning(f"创建Redis客户端失败: {str(e)}")
    
    # 配置Celery应用
    try:
        configure_celery(celery_app, config)
    except Exception as e:
        logger.warning(f"配置Celery应用失败: {str(e)}")
    
    return clients 