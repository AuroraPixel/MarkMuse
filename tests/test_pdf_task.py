#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF转Markdown任务测试脚本
测试使用多部分表单上传PDF并通过Celery任务转换为Markdown
"""

import os
import sys
import time
import json
import logging
import requests
from typing import Dict, Any, Optional
from pprint import pprint
from dotenv import load_dotenv

# 确保可以导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# API基础URL，支持通过环境变量配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def submit_pdf_task(pdf_file_path: str, task_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    提交PDF转Markdown任务，使用多部分表单上传
    
    参数:
    - pdf_file_path: PDF文件路径
    - task_options: 任务选项，如增强图片、LLM提供商等
    
    返回:
    - Dict[str, Any]: API响应
    """
    url = f"{API_BASE_URL}/tasks/pdf-to-markdown"
    
    # 获取原始文件名
    original_filename = os.path.basename(pdf_file_path)
    
    # 准备表单数据
    form_data = {}
    
    # 添加任务选项
    if task_options is None:
        task_options = {}
    
    # 设置增强图片选项
    enhance_image = task_options.get("enhance_image", True)
    form_data["enhance_image"] = "true" if enhance_image else "false"
    
    # 设置LLM提供商
    llm_provider = task_options.get("llm_provider", "openai")
    form_data["llm_provider"] = llm_provider
    
    # 设置并行处理图片数量（如果有）
    if "parallel_images" in task_options:
        form_data["parallel_images"] = str(task_options["parallel_images"])
    
    # 准备文件数据
    files = {
        "pdf_file": (original_filename, open(pdf_file_path, "rb"), "application/pdf")
    }
    
    try:
        logger.info(f"正在提交PDF转Markdown任务，文件: {original_filename}")
        response = requests.post(url, data=form_data, files=files)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"提交任务失败: {str(e)}")
        raise
    finally:
        # 确保文件对象被关闭
        files["pdf_file"][1].close()

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态
    
    参数:
    - task_id: 任务ID
    
    返回:
    - Dict[str, Any]: API响应
    """
    url = f"{API_BASE_URL}/tasks/{task_id}/status"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        raise

def wait_for_task_completion(task_id: str, max_wait: int = 600, interval: int = 5) -> Dict[str, Any]:
    """
    等待任务完成
    
    参数:
    - task_id: 任务ID
    - max_wait: 最大等待时间（秒）
    - interval: 检查间隔（秒）
    
    返回:
    - Dict[str, Any]: 最终任务状态
    """
    start_time = time.time()
    elapsed = 0
    
    logger.info(f"等待任务 {task_id} 完成，最大等待时间: {max_wait}秒")
    
    while elapsed < max_wait:
        status_response = get_task_status(task_id)
        status = status_response.get("status")
        
        # 显示当前状态
        if status == "PROGRESS" and "progress" in status_response:
            progress_meta = status_response["progress"] # 这是Celery任务的meta数据
            if progress_meta and isinstance(progress_meta, dict) and 'progress' in progress_meta and 'status' in progress_meta:
                logger.info(f"任务进度: {progress_meta['progress']}% - {progress_meta['status']}")
            elif progress_meta: # 如果 progress_meta 存在但不是预期的字典结构
                logger.info(f"任务状态: {status}, 进度详情不完整: {progress_meta}")
            else: # 如果 progress_meta 为 None
                logger.info(f"任务状态: {status}, 正在处理中...")
        else:
            logger.info(f"任务状态: {status}")
        
        # 如果任务已完成（成功或失败），返回结果
        if status in ["SUCCESS", "FAILURE"]:
            if status == "SUCCESS" and "result" in status_response:
                logger.info(f"任务成功完成，Markdown文件URL: {status_response['result']}")
            elif status == "FAILURE" and "error" in status_response:
                logger.error(f"任务失败: {status_response['error']}")
            return status_response
        
        # 等待一段时间后再次检查
        time.sleep(interval)
        elapsed = time.time() - start_time
    
    logger.warning(f"等待任务完成超时: {task_id}")
    return get_task_status(task_id)

def main():
    """主入口函数"""
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <PDF文件路径> [enhance_image=True/False] [llm_provider=openai/qianfan]")
        sys.exit(1)
    
    pdf_file_path = sys.argv[1]
    
    # 解析可选参数
    task_options = {}
    
    # 解析增强图片选项
    if len(sys.argv) > 2:
        enhance_image = sys.argv[2].lower() in ['true', 'yes', '1', 'y']
        task_options["enhance_image"] = enhance_image
    
    # 解析LLM提供商选项
    if len(sys.argv) > 3 and sys.argv[3] in ['openai', 'qianfan']:
        task_options["llm_provider"] = sys.argv[3]
    
    try:
        # 提交任务
        response = submit_pdf_task(pdf_file_path, task_options)
        task_id = response.get("task_id")
        
        if not task_id:
            logger.error("提交任务失败，未返回任务ID")
            sys.exit(1)
        
        logger.info(f"任务已提交，ID: {task_id}")
        
        # 等待任务完成
        final_status = wait_for_task_completion(task_id)
        
        # 打印最终结果
        logger.info("任务最终状态:")
        pprint(final_status)
        
        # 检查是否成功
        if final_status.get("status") == "SUCCESS":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 