"""
提示词管理模块的抽象接口定义。
提供了提示词模板和加载器的基类。
"""

import os
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Set, Union, Optional

logger = logging.getLogger(__name__)


class PromptError(Exception):
    """提示词处理相关错误的基类"""
    pass


class PromptTemplate(ABC):
    """提示词模板抽象基类"""
    
    @abstractmethod
    def render(self, params: Dict[str, Any]) -> str:
        """
        使用提供的参数渲染模板
        
        参数:
            params: 模板参数字典
            
        返回:
            渲染后的字符串
            
        异常:
            PromptError: 如果渲染失败
        """
        pass
    
    @abstractmethod
    def get_required_variables(self) -> List[str]:
        """
        获取模板所需的变量列表
        
        返回:
            变量名列表
        """
        pass
    
    @abstractmethod
    def get_template_string(self) -> str:
        """
        获取原始模板字符串
        
        返回:
            模板字符串
        """
        pass


class PromptLoader(ABC):
    """提示词加载器抽象基类"""
    
    def __init__(self, template_dir: Union[str, Path]):
        """
        初始化提示词加载器
        
        参数:
            template_dir: 模板目录路径
        """
        if isinstance(template_dir, str):
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = template_dir
            
        # 确保目录存在
        if not self.template_dir.exists():
            logger.warning(f"模板目录不存在: {self.template_dir}，尝试创建")
            try:
                os.makedirs(self.template_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"创建模板目录失败: {str(e)}")
    
    @abstractmethod
    def load(self, template_name: str) -> PromptTemplate:
        """
        加载指定名称的模板
        
        参数:
            template_name: 模板名称
            
        返回:
            模板实例
            
        异常:
            PromptError: 如果模板加载失败
        """
        pass
    
    @abstractmethod
    def register_string_template(self, name: str, template_string: str) -> PromptTemplate:
        """
        从字符串注册模板
        
        参数:
            name: 模板名称
            template_string: 模板字符串
            
        返回:
            模板实例
            
        异常:
            PromptError: 如果模板创建失败
        """
        pass 