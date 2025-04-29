"""
提示词管理器 - 负责管理和调度不同的提示词加载器
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Union

from clients.prompts.abstract_prompt import PromptLoader, PromptTemplate, PromptError
from clients.prompts.jinja_prompt import Jinja2PromptLoader
from clients.prompts.langchain_prompt import LangChainPromptLoader

logger = logging.getLogger(__name__)


class PromptManager:
    """提示词管理器 - 负责管理和调度不同的提示词加载器"""
    
    # 支持的加载器类型
    LOADER_TYPES = {
        "jinja2": Jinja2PromptLoader,
        "langchain": LangChainPromptLoader
    }
    
    def __init__(self, base_dir: Union[str, Path], default_type: str = "jinja2"):
        """
        初始化提示词管理器
        
        参数:
            base_dir: 提示词模板基础目录
            default_type: 默认加载器类型
        """
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        
        self.base_dir = base_dir
        
        if not self.base_dir.exists():
            logger.info(f"创建模板基础目录: {self.base_dir}")
            os.makedirs(self.base_dir, exist_ok=True)
        
        if default_type not in self.LOADER_TYPES:
            supported = ", ".join(self.LOADER_TYPES.keys())
            error_msg = f"不支持的加载器类型: {default_type}，支持的类型: {supported}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.default_type = default_type
        self.loaders: Dict[str, PromptLoader] = {}
        
        # 初始化默认加载器
        self._init_loader(default_type)
    
    def _init_loader(self, loader_type: str) -> PromptLoader:
        """
        初始化指定类型的加载器
        
        参数:
            loader_type: 加载器类型
            
        返回:
            加载器实例
        """
        if loader_type in self.loaders:
            return self.loaders[loader_type]
        
        # 确保加载器目录存在
        loader_dir = self.base_dir / loader_type
        if not loader_dir.exists():
            logger.info(f"创建加载器目录: {loader_dir}")
            os.makedirs(loader_dir, exist_ok=True)
        
        # 创建加载器实例
        try:
            loader_class = self.LOADER_TYPES[loader_type]
            loader = loader_class(loader_dir)
            self.loaders[loader_type] = loader
            logger.debug(f"初始化加载器 '{loader_type}' 成功")
            return loader
        except Exception as e:
            error_msg = f"初始化加载器 '{loader_type}' 失败: {str(e)}"
            logger.error(error_msg)
            raise PromptError(error_msg) from e
    
    def get_template(self, template_name: str, loader_type: Optional[str] = None) -> PromptTemplate:
        """
        获取指定名称的模板
        
        参数:
            template_name: 模板名称
            loader_type: 加载器类型，如果为None则使用默认加载器
            
        返回:
            提示词模板实例
        
        异常:
            PromptError: 如果模板加载失败
        """
        loader_type = loader_type or self.default_type
        
        if loader_type not in self.LOADER_TYPES:
            supported = ", ".join(self.LOADER_TYPES.keys())
            error_msg = f"不支持的加载器类型: {loader_type}，支持的类型: {supported}"
            logger.error(error_msg)
            raise PromptError(error_msg)
        
        loader = self._init_loader(loader_type)
        return loader.load(template_name)
    
    def render(self, template_name: str, params: Dict[str, Any], 
               loader_type: Optional[str] = None) -> str:
        """
        渲染指定名称的模板
        
        参数:
            template_name: 模板名称
            params: 模板参数
            loader_type: 加载器类型，如果为None则使用默认加载器
            
        返回:
            渲染后的字符串
        
        异常:
            PromptError: 如果模板加载或渲染失败
        """
        template = self.get_template(template_name, loader_type)
        return template.render(params)
    
    def register_string_template(self, name: str, template_string: str, 
                                loader_type: Optional[str] = None) -> PromptTemplate:
        """
        注册字符串模板
        
        参数:
            name: 模板名称
            template_string: 模板字符串
            loader_type: 加载器类型，如果为None则使用默认加载器
            
        返回:
            提示词模板实例
        
        异常:
            PromptError: 如果模板创建失败
        """
        loader_type = loader_type or self.default_type
        
        if loader_type not in self.LOADER_TYPES:
            supported = ", ".join(self.LOADER_TYPES.keys())
            error_msg = f"不支持的加载器类型: {loader_type}，支持的类型: {supported}"
            logger.error(error_msg)
            raise PromptError(error_msg)
        
        loader = self._init_loader(loader_type)
        return loader.register_string_template(name, template_string)
    
    @classmethod
    def register_loader_type(cls, name: str, loader_class: Type[PromptLoader]) -> None:
        """
        注册新的加载器类型
        
        参数:
            name: 加载器类型名称
            loader_class: 加载器类
            
        异常:
            ValueError: 如果加载器类型已存在
        """
        if name in cls.LOADER_TYPES:
            error_msg = f"加载器类型 '{name}' 已存在"
            logger.warning(error_msg)
            raise ValueError(error_msg)
        
        cls.LOADER_TYPES[name] = loader_class
        logger.info(f"注册加载器类型 '{name}' 成功") 