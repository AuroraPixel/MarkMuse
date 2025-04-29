"""
基于Jinja2模板引擎的提示词模板实现
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Union
try:
    import jinja2
except ImportError:
    raise ImportError("请安装jinja2库: pip install jinja2")

from clients.prompts.abstract_prompt import PromptTemplate, PromptLoader, PromptError

logger = logging.getLogger(__name__)


class Jinja2PromptTemplate(PromptTemplate):
    """基于Jinja2的提示词模板实现"""
    
    def __init__(self, template_string: str, template_name: Optional[str] = None):
        """
        初始化Jinja2模板
        
        参数:
            template_string: 模板字符串
            template_name: 模板名称，用于调试和日志
        """
        self.template_string = template_string
        self.template_name = template_name or "匿名模板"
        
        try:
            self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)
            self.template = self.env.from_string(template_string)
            self.variables = self._extract_variables()
        except Exception as e:
            error_msg = f"创建Jinja2模板失败 '{self.template_name}': {str(e)}"
            logger.error(error_msg)
            raise PromptError(error_msg) from e
            
    def _extract_variables(self) -> List[str]:
        """
        从模板中提取变量
        
        返回:
            变量名列表
        """
        # 使用Jinja2的AST解析器提取变量
        try:
            ast = self.env.parse(self.template_string)
            variables = set()
            
            def _visit_ast(node):
                if isinstance(node, jinja2.nodes.Name):
                    variables.add(node.name)
                for child in node.iter_child_nodes():
                    _visit_ast(child)
            
            _visit_ast(ast)
            return sorted(list(variables))
        except Exception as e:
            logger.warning(f"提取模板变量失败 '{self.template_name}': {str(e)}")
            # 使用简单的正则表达式作为备选方案
            pattern = r'{{\s*(\w+)\s*}}'
            matches = re.findall(pattern, self.template_string)
            return sorted(list(set(matches)))
    
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
        try:
            return self.template.render(**params)
        except Exception as e:
            # 找出缺少的参数
            missing_params = set(self.get_required_variables()) - set(params.keys())
            if missing_params:
                error_msg = f"渲染模板 '{self.template_name}' 失败: 缺少参数 {missing_params}"
            else:
                error_msg = f"渲染模板 '{self.template_name}' 失败: {str(e)}"
            logger.error(error_msg)
            raise PromptError(error_msg) from e
    
    def get_required_variables(self) -> List[str]:
        """
        获取模板所需的变量列表
        
        返回:
            变量名列表
        """
        return self.variables
    
    def get_template_string(self) -> str:
        """
        获取原始模板字符串
        
        返回:
            模板字符串
        """
        return self.template_string


class Jinja2PromptLoader(PromptLoader):
    """基于Jinja2的提示词加载器实现"""
    
    def __init__(self, template_dir: Union[str, Path]):
        """
        初始化Jinja2模板加载器
        
        参数:
            template_dir: 模板目录路径
        """
        super().__init__(template_dir)
        self.template_cache = {}  # 模板缓存
        
    def load(self, template_name: str) -> PromptTemplate:
        """
        加载指定名称的模板
        
        参数:
            template_name: 模板名称，可以是相对于模板目录的路径
            
        返回:
            模板实例
            
        异常:
            PromptError: 如果模板加载失败
        """
        # 检查缓存
        if template_name in self.template_cache:
            return self.template_cache[template_name]
            
        # 确保文件名有.j2后缀
        if not template_name.endswith('.j2'):
            template_name = f"{template_name}.j2"
            
        template_path = self.template_dir / template_name
        if not template_path.exists():
            error_msg = f"模板文件不存在: {template_path}"
            logger.error(error_msg)
            raise PromptError(error_msg)
            
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_string = f.read()
                
            template = Jinja2PromptTemplate(
                template_string=template_string,
                template_name=template_name
            )
            
            # 缓存模板
            self.template_cache[template_name] = template
            return template
        except Exception as e:
            error_msg = f"加载模板 '{template_name}' 失败: {str(e)}"
            logger.error(error_msg)
            raise PromptError(error_msg) from e
    
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
        try:
            template = Jinja2PromptTemplate(
                template_string=template_string,
                template_name=name
            )
            
            # 缓存模板
            self.template_cache[name] = template
            return template
        except Exception as e:
            error_msg = f"从字符串创建模板 '{name}' 失败: {str(e)}"
            logger.error(error_msg)
            raise PromptError(error_msg) from e 