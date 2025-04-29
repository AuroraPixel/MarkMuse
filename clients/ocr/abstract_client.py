"""
OCR 客户端抽象接口
定义所有 OCR 服务必须实现的方法
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class OCRClientError(Exception):
    """OCR 客户端错误基类"""
    pass


class OCRClient(ABC):
    """
    OCR 客户端抽象接口
    所有具体的 OCR 实现都应该继承自此类
    """
    
    @abstractmethod
    def process(
        self,
        model: str,
        document: Dict[str, Any],
        include_image_base64: bool = False
    ) -> Optional[Any]:
        """
        调用 OCR 服务处理文档
        
        参数:
        - model: 模型名称
        - document: 文档数据
        - include_image_base64: 是否包含图片的 base64 数据
        
        返回:
        - 处理结果，失败返回 None
        
        抛出:
        - OCRClientError: 处理失败
        """
        pass 