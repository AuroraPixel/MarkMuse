from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Optional, AsyncIterator, Union

class LLMClientError(Exception):
    """LLM 客户端通用异常类"""
    pass

class LLMClient(ABC):
    """
    LLM 客户端抽象基类，定义所有 LLM 能力的通用接口。
    
    每个 LLM 提供商的具体实现需要继承此类并实现相关方法。
    """
    
    @classmethod
    @abstractmethod
    def supported_capabilities(cls) -> Set[str]:
        """
        返回该 LLM 客户端支持的所有能力集合
        """
        pass
        
    @property
    def runtime_capabilities(self) -> Set[str]:
        """
        返回当前客户端实例运行时实际可用的能力集合
        （考虑配置、API权限等因素）
        """
        return self.supported_capabilities()
    
    def has_capability(self, capability: str) -> bool:
        """
        检查当前客户端是否支持指定的能力
        """
        return capability in self.runtime_capabilities
    
    @staticmethod
    def should_print_typing_output() -> bool:
        """
        检查是否应该输出打字效果（流式输出）
        根据环境变量LOG_LEVEL判断，只有在DEBUG模式才输出
        
        返回:
            bool: 是否应该输出打字效果
        """
        import os
        return os.environ.get('LOG_LEVEL', 'INFO').upper() == 'DEBUG'
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        进行文本聊天/生成
        
        参数:
            messages: 消息列表，格式为 [{role: "user", content: "..."}, ...]
            **kwargs: 额外参数
            
        返回:
            生成的文本响应
        """
        pass
    
    @abstractmethod
    def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[str]:
        """
        流式文本生成
        
        参数:
            messages: 消息列表
            **kwargs: 额外参数
            
        返回:
            生成的文本响应流
        """
        pass
    
    @abstractmethod
    def analyze_image(self, image_base64: str, img_id: str, **kwargs) -> str:
        """
        分析图片（Base64格式）
        
        参数:
            image_base64: Base64 编码的图片数据
            img_id: 图片ID
            **kwargs: 额外参数
            
        返回:
            图片分析描述
        """
        pass
    
    @abstractmethod
    def analyze_image_streaming(self, image_base64: str, img_id: str, **kwargs) -> str:
        """
        流式分析图片（Base64格式）
        
        参数:
            image_base64: Base64 编码的图片数据
            img_id: 图片ID
            **kwargs: 额外参数
            
        返回:
            图片分析描述
        """
        pass
    
    @abstractmethod
    def analyze_image_url(self, image_url: str, analysis_prompt: Optional[str] = None, **kwargs) -> str:
        """
        分析图片（URL格式）
        
        参数:
            image_url: 图片URL
            analysis_prompt: 分析提示词
            **kwargs: 额外参数
            
        返回:
            图片分析描述
        """
        pass 