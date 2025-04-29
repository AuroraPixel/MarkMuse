#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提示词管理器使用示例
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.prompts import (
    PromptManager, 
    PromptError,
    Jinja2PromptTemplate,
    LangChainPromptTemplate
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_jinja2_template():
    """测试Jinja2模板"""
    logger.info("=== 测试Jinja2模板 ===")
    
    # 创建模板
    template_string = """
    你好，{{ name }}！
    
    今天是{{ date }}，天气{{ weather }}。
    
    {% if tasks %}
    你的任务列表:
    {% for task in tasks %}
    - {{ task }}
    {% endfor %}
    {% else %}
    今天没有安排任务。
    {% endif %}
    """
    
    template = Jinja2PromptTemplate(template_string, "greeting")
    
    # 获取并显示所需变量
    required_vars = template.get_required_variables()
    logger.info(f"模板所需变量: {required_vars}")
    
    # 渲染模板 - 有任务的情况
    params = {
        "name": "张三",
        "date": "2023年10月1日",
        "weather": "晴朗",
        "tasks": ["买菜", "写代码", "读书"]
    }
    
    result = template.render(params)
    logger.info(f"渲染结果 (有任务):\n{result}")
    
    # 渲染模板 - 无任务的情况
    params = {
        "name": "李四",
        "date": "2023年10月2日",
        "weather": "多云",
        "tasks": []
    }
    
    result = template.render(params)
    logger.info(f"渲染结果 (无任务):\n{result}")
    
    # 渲染模板 - 缺少参数
    try:
        params = {
            "name": "王五",
            "weather": "下雨"
        }
        
        result = template.render(params)
    except PromptError as e:
        logger.error(f"预期的错误 (缺少参数): {str(e)}")


def test_langchain_template():
    """测试LangChain模板"""
    logger.info("=== 测试LangChain模板 ===")
    
    # 创建模板
    template_string = """
    你好，{name}！
    
    我们正在讨论{topic}。
    
    请告诉我你对{topic}的看法，特别是关于{aspect}方面。
    """
    
    template = LangChainPromptTemplate(template_string, "discussion")
    
    # 获取并显示所需变量
    required_vars = template.get_required_variables()
    logger.info(f"模板所需变量: {required_vars}")
    
    # 渲染模板
    params = {
        "name": "张教授",
        "topic": "人工智能",
        "aspect": "伦理"
    }
    
    result = template.render(params)
    logger.info(f"渲染结果:\n{result}")
    
    # 渲染模板 - 缺少参数
    try:
        params = {
            "name": "李教授",
            "topic": "机器学习"
        }
        
        result = template.render(params)
    except PromptError as e:
        logger.error(f"预期的错误 (缺少参数): {str(e)}")


def test_prompt_manager():
    """测试提示词管理器"""
    logger.info("=== 测试提示词管理器 ===")
    
    # 获取示例目录
    examples_dir = Path(__file__).parent
    prompts_dir = examples_dir / "prompts"
    
    # 创建提示词管理器
    manager = PromptManager(prompts_dir)
    
    # 从文件加载Jinja2模板
    try:
        ocr_template = manager.get_template("ocr_analysis", "jinja2")
        
        params = {
            "ocr_text": "发票\n日期: 2023年10月1日\n金额: ¥1,234.56\n发票号: INV-2023-001\n",
            "document_type": "增值税发票"
        }
        
        result = ocr_template.render(params)
        logger.info(f"OCR分析模板结果:\n{result}")
    except PromptError as e:
        logger.error(f"加载OCR模板失败: {str(e)}")
    
    # 从文件加载LangChain模板
    try:
        image_template = manager.get_template("image_analysis", "langchain")
        
        params = {
            "image_url": "https://example.com/image.jpg",
            "analysis_depth": "详细",
            "focus_area": "中心区域的文字内容"
        }
        
        result = image_template.render(params)
        logger.info(f"图像分析模板结果:\n{result}")
    except PromptError as e:
        logger.error(f"加载图像分析模板失败: {str(e)}")
    
    # 注册字符串模板
    string_template = """
    这是一个简单的{template_type}模板。
    当前时间是{time}。
    """
    
    template = manager.register_string_template(
        "simple", 
        string_template, 
        "langchain"
    )
    
    params = {
        "template_type": "字符串",
        "time": "下午3点"
    }
    
    result = template.render(params)
    logger.info(f"字符串模板结果:\n{result}")


if __name__ == "__main__":
    try:
        # 测试各个功能
        test_jinja2_template()
        test_langchain_template()
        test_prompt_manager()
        
        logger.info("所有测试完成")
        
    except Exception as e:
        logger.exception(f"测试过程中发生错误: {str(e)}")
        sys.exit(1) 