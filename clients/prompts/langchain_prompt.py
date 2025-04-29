"""
基于LangChain的提示词模板实现
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union

try:
    from langchain_core.prompts import PromptTemplate as LCPromptTemplate
except ImportError:
    raise ImportError("请安装LangChain: pip install langchain-core")

from clients.prompts.abstract_prompt import PromptTemplate, PromptLoader, PromptError

logger = logging.getLogger(__name__)


class LangChainPromptTemplate(PromptTemplate):
    """LangChain提示词模板实现"""
    
    def __init__(self, template_string: str, template_name: Optional[str] = None):
        """
        初始化LangChain提示词模板
        
        参数:
            template_string: 模板字符串
            template_name: 模板名称，可选
        """
        self.template_string = template_string
        self.template_name = template_name
        
        try:
            # 提取变量
            self.variables = self._extract_variables()
            
            # 创建LangChain模板
            self.template = LCPromptTemplate.from_template(template_string)
            
        except Exception as e:
            raise PromptError(f"无法创建LangChain模板: {str(e)}")
    
    def _extract_variables(self) -> Set[str]:
        """
        从模板中提取变量
        
        返回:
            变量名集合
        """
        try:
            # 查找模板中的所有 {variable} 格式的变量
            variables = set(re.findall(r'\{([^{}]+)\}', self.template_string))
            return variables
        except Exception as e:
            raise PromptError(f"提取模板变量时发生错误: {str(e)}")
    
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
        # 检查所有必需的变量是否都提供了
        missing_vars = self.variables - set(params.keys())
        if missing_vars:
            missing_list = ", ".join(missing_vars)
            template_info = f" '{self.template_name}'" if self.template_name else ""
            raise PromptError(f"模板{template_info}缺少必需的变量: {missing_list}")
        
        try:
            # 只传递模板中需要的参数
            template_params = {k: v for k, v in params.items() if k in self.variables}
            return self.template.format(**template_params)
        except Exception as e:
            template_info = f" '{self.template_name}'" if self.template_name else ""
            raise PromptError(f"渲染模板{template_info}时发生错误: {str(e)}")
    
    def get_required_variables(self) -> List[str]:
        """
        获取模板所需的变量列表
        
        返回:
            变量名列表
        """
        return list(self.variables)
    
    def get_template_string(self) -> str:
        """
        获取原始模板字符串
        
        返回:
            模板字符串
        """
        return self.template_string


class LangChainPromptLoader(PromptLoader):
    """LangChain提示词加载器实现"""
    
    def __init__(self, template_dir: Union[str, Path]):
        """
        初始化LangChain提示词加载器
        
        参数:
            template_dir: 模板目录路径
        """
        super().__init__(template_dir)
        self._template_cache: Dict[str, LangChainPromptTemplate] = {}
    
    def load(self, template_name: str) -> LangChainPromptTemplate:
        """
        加载指定名称的模板
        
        参数:
            template_name: 模板名称
            
        返回:
            LangChain模板实例
            
        异常:
            PromptError: 如果模板加载失败
        """
        # 检查缓存
        if template_name in self._template_cache:
            logger.debug(f"从缓存加载模板 '{template_name}'")
            return self._template_cache[template_name]
        
        # 确保文件名有正确的扩展名
        if not template_name.endswith('.txt'):
            file_name = f"{template_name}.txt"
        else:
            file_name = template_name
        
        file_path = self.template_dir / file_name
        
        try:
            if not os.path.exists(file_path):
                raise PromptError(f"模板文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                template_string = f.read().strip()
            
            template = LangChainPromptTemplate(template_string, template_name)
            
            # 缓存模板
            self._template_cache[template_name] = template
            
            logger.debug(f"成功加载模板 '{template_name}'")
            return template
            
        except PromptError:
            raise
        except Exception as e:
            raise PromptError(f"加载模板 '{template_name}' 时发生错误: {str(e)}")
    
    def register_string_template(self, name: str, template_string: str) -> LangChainPromptTemplate:
        """
        从字符串注册模板
        
        参数:
            name: 模板名称
            template_string: 模板字符串
            
        返回:
            LangChain模板实例
            
        异常:
            PromptError: 如果模板创建失败
        """
        try:
            template = LangChainPromptTemplate(template_string, name)
            
            # 缓存模板
            self._template_cache[name] = template
            
            logger.debug(f"成功注册字符串模板 '{name}'")
            return template
            
        except PromptError:
            raise
        except Exception as e:
            raise PromptError(f"注册字符串模板 '{name}' 时发生错误: {str(e)}") 