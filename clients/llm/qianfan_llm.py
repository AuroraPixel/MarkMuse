"""
百度千帆 LLM 客户端实现
封装百度千帆 API 的文本生成、图片分析等多模态能力
"""

import logging
import os
from typing import Any, Dict, List, Set, Optional, AsyncIterator, Union

from .abstract_llm import LLMClient, LLMClientError

logger = logging.getLogger(__name__)


class QianfanLLMClient(LLMClient):
    """
    百度千帆 LLM 客户端
    基于百度千帆 API 实现通用 LLM 能力
    """
    
    @classmethod
    def supported_capabilities(cls) -> Set[str]:
        """返回百度千帆支持的所有能力"""
        return {
            "chat",                  # 文本对话
            "streaming",             # 流式输出
            # 注意：目前千帆不支持直接的多模态，以下能力是预留的
            # "image_analysis",        # 图片分析
            # "vision"                 # 视觉理解
        }
    
    def __init__(self, ak: str, sk: str, model_name: str = "ERNIE-Bot-4"):
        """
        初始化百度千帆 LLM 客户端
        
        参数:
        - ak: 百度千帆 Access Key
        - sk: 百度千帆 Secret Key
        - model_name: 模型名称，默认为 "ERNIE-Bot-4"
        """
        self.ak = ak
        self.sk = sk
        self.model_name = model_name
        self.model = None
        
        # 运行时能力集合
        self._runtime_capabilities = self.supported_capabilities()
        
        try:
            # 设置环境变量，千帆 SDK 需要
            os.environ["QIANFAN_AK"] = ak
            os.environ["QIANFAN_SK"] = sk
            
            from langchain_community.llms import QianfanLLMEndpoint
            self.model = QianfanLLMEndpoint(model=model_name, streaming=True)
            logger.info(f"已初始化百度千帆 LLM 客户端 (模型: {model_name})")
        except ImportError:
            logger.error("使用千帆需安装 langchain-community，请执行: pip install langchain-community")
            raise LLMClientError("使用千帆需安装 langchain-community")
        except Exception as e:
            logger.error(f"初始化百度千帆 LLM 客户端失败: {str(e)}")
            raise LLMClientError(f"初始化百度千帆 LLM 客户端失败: {str(e)}")
    
    @property
    def runtime_capabilities(self) -> Set[str]:
        """返回当前客户端实例运行时实际可用的能力集合"""
        return self._runtime_capabilities
    
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """进行文本聊天/生成"""
        if not self.model:
            raise LLMClientError("百度千帆模型未初始化")
        
        try:
            # 千帆目前使用字符串作为输入，我们需要将消息列表转换为单个提示字符串
            prompt = self._format_messages_to_prompt(messages)
            response = self.model.invoke(prompt)
            return response
        except Exception as e:
            logger.error(f"百度千帆聊天请求失败: {str(e)}")
            raise LLMClientError(f"百度千帆聊天请求失败: {str(e)}")
    
    def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[str]:
        """流式文本生成"""
        if not self.model:
            raise LLMClientError("百度千帆模型未初始化")
        
        # 千帆目前使用字符串作为输入，我们需要将消息列表转换为单个提示字符串
        prompt = self._format_messages_to_prompt(messages)
        
        # 返回流式响应
        try:
            return self.model.stream(prompt)
        except Exception as e:
            logger.error(f"百度千帆流式请求失败: {str(e)}")
            raise LLMClientError(f"百度千帆流式请求失败: {str(e)}")
    
    def analyze_image(self, image_base64: str, img_id: str, **kwargs) -> str:
        """分析图片内容 (非流式)"""
        # 千帆暂不支持直接多模态
        logger.warning("百度千帆图片分析功能暂不支持直接多模态能力")
        return "图片分析功能暂不支持千帆接口"
    
    def analyze_image_streaming(self, image_base64: str, img_id: str, **kwargs) -> str:
        """流式分析图片内容并实时输出结果"""
        # 千帆暂不支持直接多模态
        logger.warning("百度千帆图片分析功能暂不支持直接多模态能力")
        return "图片流式分析功能暂不支持千帆接口"
    
    def analyze_image_url(self, image_url: str, analysis_prompt: Optional[str] = None, **kwargs) -> str:
        """通过远程 URL 分析图片内容"""
        # 千帆暂不支持直接多模态
        logger.warning("百度千帆图片分析功能暂不支持直接多模态能力")
        return "图片URL分析功能暂不支持千帆接口"
    
    def _format_messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """将消息列表格式化为单个提示字符串"""
        formatted_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted_messages.append(f"System: {content}")
            elif role == "user":
                formatted_messages.append(f"用户: {content}")
            elif role == "assistant":
                formatted_messages.append(f"助手: {content}")
        
        # 组合成一个字符串
        return "\n".join(formatted_messages) 