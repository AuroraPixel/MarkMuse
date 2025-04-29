"""
百度千帆图片分析器实现
封装百度千帆 API 的图片分析功能
"""

import logging
import os
from typing import Optional

from .abstract_analyzer import ImageAnalyzer, ImageAnalyzerError

logger = logging.getLogger(__name__)


class QianfanImageAnalyzer(ImageAnalyzer):
    """
    百度千帆图片分析器
    基于百度千帆 API 实现图片分析
    """
    
    def __init__(self, ak: str, sk: str, model_name: str = "qianfan-vl-plus"):
        """
        初始化百度千帆图片分析器
        
        参数:
        - ak: 百度千帆 Access Key
        - sk: 百度千帆 Secret Key
        - model_name: 模型名称，默认为 "qianfan-vl-plus"
        """
        self.ak = ak
        self.sk = sk
        self.model_name = model_name
        self.model = None
        
        try:
            # 设置环境变量，千帆 SDK 需要
            os.environ["QIANFAN_AK"] = ak
            os.environ["QIANFAN_SK"] = sk
            
            from langchain_community.llms import QianfanLLMEndpoint
            self.model = QianfanLLMEndpoint(model=model_name)
            logger.info(f"已初始化百度千帆图片分析器 (模型: {model_name})")
        except ImportError:
            logger.error("使用千帆需安装 langchain-community，请执行: pip install langchain-community")
            raise ImageAnalyzerError("使用千帆需安装 langchain-community")
        except Exception as e:
            logger.error(f"初始化百度千帆图片分析器失败: {str(e)}")
            raise ImageAnalyzerError(f"初始化百度千帆图片分析器失败: {str(e)}")
    
    def analyze_image(self, image_base64: str) -> str:
        """分析图片内容 (非流式)"""
        if not self.model:
            return ""
            
        # 注意：目前千帆不支持直接的多模态，这里只是预留 API
        logger.warning("百度千帆图片分析功能暂不支持直接多模态能力")
        return "图片分析功能暂不支持千帆接口"
    
    def analyze_image_streaming(self, image_base64: str, img_id: str) -> str:
        """流式分析图片内容并实时输出结果"""
        if not self.model:
            return ""
            
        # 注意：目前千帆不支持直接的多模态，这里只是预留 API
        logger.warning("百度千帆图片分析功能暂不支持直接多模态能力")
        return "图片流式分析功能暂不支持千帆接口" 