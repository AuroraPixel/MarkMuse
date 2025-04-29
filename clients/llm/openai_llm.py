"""
OpenAI LLM 客户端实现
封装 OpenAI API 的文本生成、图片分析等多模态能力
"""

import logging
from typing import Any, Dict, List, Set, Optional, AsyncIterator, Union

from .abstract_llm import LLMClient, LLMClientError

logger = logging.getLogger(__name__)


class OpenAILLMClient(LLMClient):
    """
    OpenAI LLM 客户端
    基于 OpenAI API 实现通用 LLM 能力
    """
    
    @classmethod
    def supported_capabilities(cls) -> Set[str]:
        """返回 OpenAI 支持的所有能力"""
        return {
            "chat",                  # 文本对话
            "streaming",             # 流式输出
            "image_analysis",        # 图片分析
            "function_calling",      # 函数调用
            "vision"                 # 视觉理解
        }
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o", base_url: Optional[str] = None):
        """
        初始化 OpenAI LLM 客户端
        
        参数:
        - api_key: OpenAI API 密钥
        - model_name: 模型名称，默认为 "gpt-4o"
        - base_url: 可选的 API 基础 URL
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.model = None
        
        # 运行时能力集合（可能会根据模型和配置有所不同）
        self._runtime_capabilities = self.supported_capabilities()
        
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
            logger.info(f"已初始化 OpenAI LLM 客户端 (模型: {model_name})")
            
            # 检查模型能力
            if not model_name.startswith(("gpt-4-vision", "gpt-4o")):
                self._runtime_capabilities.discard("vision")
                self._runtime_capabilities.discard("image_analysis")
                logger.warning(f"模型 {model_name} 可能不支持图像分析功能")
                
        except ImportError:
            logger.error("使用 OpenAI 需安装 langchain-openai，请执行: pip install langchain-openai")
            raise LLMClientError("使用 OpenAI 需安装 langchain-openai")
        except Exception as e:
            logger.error(f"初始化 OpenAI LLM 客户端失败: {str(e)}")
            raise LLMClientError(f"初始化 OpenAI LLM 客户端失败: {str(e)}")
    
    @property
    def runtime_capabilities(self) -> Set[str]:
        """返回当前客户端实例运行时实际可用的能力集合"""
        return self._runtime_capabilities
        
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """进行文本聊天/生成"""
        if not self.model:
            raise LLMClientError("OpenAI 模型未初始化")
            
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
            
            # 转换消息格式为 LangChain 格式
            lc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
            
            # 调用模型
            response = self.model.invoke(lc_messages)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI 聊天请求失败: {str(e)}")
            raise LLMClientError(f"OpenAI 聊天请求失败: {str(e)}")
    
    def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[str]:
        """流式文本生成"""
        if not self.model:
            raise LLMClientError("OpenAI 模型未初始化")
            
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
            
            # 转换消息格式为 LangChain 格式
            lc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
            
            # 返回流式响应
            return self.model.stream(lc_messages)
        except Exception as e:
            logger.error(f"OpenAI 流式请求失败: {str(e)}")
            raise LLMClientError(f"OpenAI 流式请求失败: {str(e)}")
    
    def analyze_image(self, image_base64: str, img_id: str, **kwargs) -> str:
        """分析图片内容 (非流式)"""
        if not self.model:
            raise LLMClientError("OpenAI 模型未初始化")
        
        if "image_analysis" not in self.runtime_capabilities:
            raise LLMClientError("当前模型不支持图片分析功能")
            
        try:
            from langchain_core.messages import HumanMessage
            
            # 获取或使用默认的分析提示词
            prompt = kwargs.get("analysis_prompt", self.get_default_prompt())
            
            response = self.model.invoke([
                HumanMessage(content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }}
                ])
            ])
            return response.content
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            raise LLMClientError(f"图片分析失败: {str(e)}")
    
    def analyze_image_streaming(self, image_base64: str, img_id: str, **kwargs) -> str:
        """流式分析图片内容并实时输出结果"""
        if not self.model:
            raise LLMClientError("OpenAI 模型未初始化")
        
        if "image_analysis" not in self.runtime_capabilities:
            raise LLMClientError("当前模型不支持图片分析功能")
            
        try:
            from langchain_core.messages import HumanMessage
            
            # 获取或使用默认的分析提示词
            prompt = kwargs.get("analysis_prompt", self.get_default_prompt())
            
            full_response = ""
            logger.info(f"开始分析图片: {img_id}")
            print(f"\n开始分析图片 {img_id} ...", end="", flush=True)
            
            for chunk in self.model.stream([
                HumanMessage(content=[
                    {"type": "text", "text": prompt},
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
            raise LLMClientError(f"图片流式分析失败: {str(e)}")
    
    def analyze_image_url(self, image_url: str, analysis_prompt: Optional[str] = None, **kwargs) -> str:
        """通过远程 URL 分析图片内容"""
        if not self.model:
            raise LLMClientError("OpenAI 模型未初始化")
        
        if "image_analysis" not in self.runtime_capabilities:
            raise LLMClientError("当前模型不支持图片分析功能")
            
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
            raise LLMClientError(f"远程图片分析失败: {str(e)}")
            
    def get_default_prompt(self) -> str:
        """重写默认提示词"""
        return ("请详细分析此图片内容，包括但不限于：\n"
                "1. 图片中的主体对象及其关系\n"
                "2. 文字信息（如有）\n"
                "3. 数据可视化图表的解读（如适用）\n"
                "4. 整体语义理解\n"
                "输出使用简洁明了的中文描述") 