"""
OCR 客户端模块，提供各种 OCR 服务的统一接口
"""

from .abstract_client import OCRClient
from .mistral_client import MistralOCRClient

__all__ = ['OCRClient', 'MistralOCRClient'] 