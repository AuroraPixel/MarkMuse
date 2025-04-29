"""
图片分析器抽象接口
定义所有图片分析服务必须实现的方法
"""

from abc import ABC, abstractmethod
from typing import Optional


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

    @abstractmethod
    def analyze_image_url(self, image_url: str, analysis_prompt: Optional[str] = None) -> str:
        """
        通过远程 URL 分析图片内容
        
        参数:
        - image_url: 图片的远程 URL
        - analysis_prompt: 可选的分析提示词，指导 AI 如何分析图片
        
        返回:
        - 分析结果文本
        
        抛出:
        - ImageAnalyzerError: 分析失败
        """
        pass
    
    def get_default_prompt(self) -> str:
        """可重写的默认提示词模板"""
        return ("请详细分析此图片内容，包括但不限于：\n"
                "1. 图片中的主体对象及其关系\n"
                "2. 文字信息（如有）\n"
                "3. 数据可视化图表的解读（如适用）\n"
                "4. 整体语义理解\n"
                "输出使用简洁明了的中文描述") 