"""
OpenAI 图片分析器实现
封装 OpenAI 多模态 API 的图片分析功能
"""

import logging
from typing import Optional

from .abstract_analyzer import ImageAnalyzer, ImageAnalyzerError

logger = logging.getLogger(__name__)


class OpenAIImageAnalyzer(ImageAnalyzer):
    """
    OpenAI 图片分析器
    基于 OpenAI 多模态模型实现图片分析
    """
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o", base_url: Optional[str] = None):
        """
        初始化 OpenAI 图片分析器
        
        参数:
        - api_key: OpenAI API 密钥
        - model_name: 模型名称，默认为 "gpt-4o"
        - base_url: 可选的 API 基础 URL
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.model = None
        
        try:
            from langchain_openai import ChatOpenAI
            
            # 构建初始化参数
            model_kwargs = {
                "model": model_name,
                "max_tokens": None,
                "api_key": api_key,
                "temperature": 0.1,
                "max_retries": 3,
                "timeout": 30,
                "streaming": True,  # 启用流式输出
            }
            
            # 如果设置了自定义基础 URL，则添加到参数中
            if base_url:
                model_kwargs["base_url"] = base_url
                logger.info(f"使用自定义 OpenAI API 基础 URL: {base_url}")
            
            self.model = ChatOpenAI(**model_kwargs)
            logger.info(f"已初始化 OpenAI 图片分析器 (模型: {model_name})")
        except ImportError:
            logger.error("使用 OpenAI 需安装 langchain-openai，请执行: pip install langchain-openai")
            raise ImageAnalyzerError("使用 OpenAI 需安装 langchain-openai")
        except Exception as e:
            logger.error(f"初始化 OpenAI 图片分析器失败: {str(e)}")
            raise ImageAnalyzerError(f"初始化 OpenAI 图片分析器失败: {str(e)}")
    
    def analyze_image(self, image_base64: str) -> str:
        """分析图片内容 (非流式)"""
        if not self.model:
            return ""
            
        try:
            from langchain_core.messages import HumanMessage
            
            response = self.model.invoke([
                HumanMessage(content=[
                    {"type": "text", "text": "详细描述此图片内容，关注图片中的文字、数据和关键信息，使用中文回复。"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }}
                ])
            ])
            return response.content
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            raise ImageAnalyzerError(f"图片分析失败: {str(e)}")
    
    def analyze_image_streaming(self, image_base64: str, img_id: str) -> str:
        """流式分析图片内容并实时输出结果"""
        if not self.model:
            return ""
            
        try:
            from langchain_core.messages import HumanMessage
            
            full_response = ""
            logger.info(f"开始分析图片: {img_id}")
            print(f"\n开始分析图片 {img_id} ...", end="", flush=True)
            
            for chunk in self.model.stream([
                HumanMessage(content=[
                    {"type": "text", "text": "详细描述此图片内容，关注图片中的文字、数据和关键信息，使用中文回复。"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }}
                ])
            ]):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    full_response += content
                    print(content, end="", flush=True)
            
            print("\n图片分析完成\n", flush=True)
            logger.info(f"图片 {img_id} 分析完成")
            return full_response
        except Exception as e:
            logger.error(f"图片流式分析失败: {str(e)}")
            raise ImageAnalyzerError(f"图片流式分析失败: {str(e)}")
    
    def analyze_image_url(self, image_url: str, analysis_prompt: Optional[str] = None) -> str:
        """通过远程 URL 分析图片内容"""
        if not self.model:
            logger.error("OpenAI 模型未初始化")
            return ""
            
        try:
            from langchain_core.messages import HumanMessage
            
            # 使用传入的提示词或默认提示词
            prompt = analysis_prompt or self.get_default_prompt()
            
            logger.info(f"开始分析远程图片: {image_url}")
            print(f"\n开始分析图片 (URL模式) ...", end="", flush=True)
            
            # 流式处理
            full_response = ""
            for chunk in self.model.stream([
                HumanMessage(content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ])
            ]):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    full_response += content
                    print(content, end="", flush=True)
            
            print("\n图片分析完成\n", flush=True)
            logger.info(f"远程图片 URL 分析完成")
            return full_response
            
        except Exception as e:
            logger.error(f"远程图片分析失败: {str(e)}")
            raise ImageAnalyzerError(f"远程图片分析失败: {str(e)}")
            
    def get_default_prompt(self) -> str:
        """重写默认提示词"""
        return ("请详细分析此图片内容，包括但不限于：\n"
                "1. 图片中的主体对象及其关系\n"
                "2. 文字信息（如有）\n"
                "3. 数据可视化图表的解读（如适用）\n"
                "4. 整体语义理解\n"
                "输出使用简洁明了的中文描述") 