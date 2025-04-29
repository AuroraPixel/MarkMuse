"""
Mistral OCR 客户端实现
封装 Mistral SDK 的 OCR 功能
"""

import logging
from typing import Any, Dict, Optional

from mistralai import Mistral
from .abstract_client import OCRClient, OCRClientError

logger = logging.getLogger(__name__)


class MistralOCRClient(OCRClient):
    """
    Mistral OCR 客户端
    基于 Mistral SDK 实现 OCR 服务
    """
    
    def __init__(self, api_key: str):
        """
        初始化 Mistral OCR 客户端
        
        参数:
        - api_key: Mistral API 密钥
        """
        try:
            self.client = Mistral(api_key=api_key)
            self.ocr = self.client.ocr
            logger.info("已初始化 Mistral OCR 客户端")
        except Exception as e:
            logger.error(f"初始化 Mistral OCR 客户端失败: {str(e)}")
            raise OCRClientError(f"初始化 Mistral OCR 客户端失败: {str(e)}")
    
    def process(
        self,
        model: str,
        document: Dict[str, Any],
        include_image_base64: bool = False
    ) -> Optional[Any]:
        """
        调用 Mistral OCR 服务处理文档
        
        参数:
        - model: 模型名称，例如 "mistral-ocr-latest"
        - document: 文档数据，例如 {"type": "document_url", "document_url": "..."}
        - include_image_base64: 是否包含图片的 base64 数据
        
        返回:
        - OCR 处理结果
        
        抛出:
        - OCRClientError: 处理失败
        """
        try:
            return self.ocr.process(
                model=model,
                document=document,
                include_image_base64=include_image_base64
            )
        except Exception as e:
            error_message = str(e).lower()
            
            # 分类错误类型
            if "api key" in error_message or "authentication" in error_message:
                logger.error(f"Mistral API 认证错误: {str(e)}")
                raise OCRClientError(f"Mistral API 认证错误: {str(e)}")
            elif "rate limit" in error_message or "too many requests" in error_message:
                logger.error(f"Mistral API 速率限制: {str(e)}")
                raise OCRClientError(f"Mistral API 速率限制: {str(e)}")
            else:
                logger.error(f"Mistral OCR 处理失败: {str(e)}")
                raise OCRClientError(f"Mistral OCR 处理失败: {str(e)}") 