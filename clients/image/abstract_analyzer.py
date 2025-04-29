"""
图片分析器抽象接口
定义所有图片分析服务必须实现的方法
"""

from abc import ABC, abstractmethod


class ImageAnalyzerError(Exception):
    """图片分析器错误基类"""
    pass


class ImageAnalyzer(ABC):
    """
    图片分析器抽象接口
    所有具体的图片分析实现都应该继承自此类
    """
    
    @abstractmethod
    def analyze_image(self, image_base64: str) -> str:
        """
        分析图片内容（非流式）
        
        参数:
        - image_base64: base64 编码的图片数据
        
        返回:
        - 分析结果文本
        
        抛出:
        - ImageAnalyzerError: 分析失败
        """
        pass
    
    @abstractmethod
    def analyze_image_streaming(self, image_base64: str, img_id: str) -> str:
        """
        流式分析图片内容
        
        参数:
        - image_base64: base64 编码的图片数据
        - img_id: 图片 ID，用于日志和输出标识
        
        返回:
        - 分析结果文本
        
        抛出:
        - ImageAnalyzerError: 分析失败
        """
        pass 