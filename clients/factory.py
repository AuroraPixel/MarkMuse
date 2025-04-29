"""
客户端工厂模块
提供创建各种客户端实例的工厂函数
"""

import logging
from typing import Optional, Dict

from config import APIConfig
from clients.ocr import OCRClient, MistralOCRClient
from clients.image import ImageAnalyzer, OpenAIImageAnalyzer, QianfanImageAnalyzer
from clients.storage import S3Storage

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


def create_image_analyzer(config: APIConfig, provider: str = "openai") -> Optional[ImageAnalyzer]:
    """
    创建图片分析器
    
    参数:
    - config: API 配置
    - provider: 提供商，支持 'openai' 和 'qianfan'
    
    返回:
    - ImageAnalyzer: 图片分析器实例，如果创建失败则返回 None
    """
    try:
        if provider == "openai":
            if not config.openai_api_key:
                logger.warning("未设置 OpenAI API 密钥，无法创建图片分析器")
                return None
            
            return OpenAIImageAnalyzer(
                api_key=config.openai_api_key,
                model_name=config.openai_model_name,
                base_url=config.openai_base_url
            )
        elif provider == "qianfan":
            if not config.qianfan_ak or not config.qianfan_sk:
                logger.warning("未设置百度千帆 AK/SK，无法创建图片分析器")
                return None
            
            return QianfanImageAnalyzer(
                ak=config.qianfan_ak,
                sk=config.qianfan_sk
            )
        else:
            logger.error(f"不支持的图片分析器提供商: {provider}")
            return None
    except Exception as e:
        logger.error(f"创建图片分析器失败: {str(e)}")
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


def create_clients(config: APIConfig, image_provider: str = "openai") -> Dict[str, any]:
    """
    创建所有必要的客户端
    
    参数:
    - config: API 配置
    - image_provider: 图片分析提供商
    
    返回:
    - Dict: 包含各种客户端的字典
    """
    clients = {
        "ocr_client": create_ocr_client(config),
        "image_analyzer": None,
        "storage_client": None
    }
    
    # 如果需要图片分析
    if image_provider:
        clients["image_analyzer"] = create_image_analyzer(config, image_provider)
    
    # 尝试创建存储客户端
    if hasattr(config, 's3_access_key') and config.s3_access_key:
        clients["storage_client"] = create_storage_client(config)
    
    return clients 