#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF转Markdown任务测试脚本
测试clients.celery.pdf_processing_tasks.transcribe_pdf_to_md_task的功能
"""

import os
import sys
import time
import json
import base64
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
    提交PDF转Markdown任务
    
    参数:
    - pdf_file_path: PDF文件路径
    - task_options: 任务选项，如增强图片、LLM提供商等
    
    返回:
    - Dict[str, Any]: API响应
    """
    url = f"{API_BASE_URL}/tasks/submit"
    
    # 读取PDF文件并编码为base64
    try:
        with open(pdf_file_path, 'rb') as f:
            pdf_content = f.read()
        pdf_content_base64 = base64.b64encode(pdf_content).decode('utf-8')
    except Exception as e:
        logger.error(f"读取PDF文件失败: {str(e)}")
        raise
    
    # 获取原始文件名
    original_filename = os.path.basename(pdf_file_path)
    
    # 默认任务选项
    if task_options is None:
        task_options = {
            "enhance_image": True,
            "llm_provider": "openai"
        }
    
    # 构建请求载荷
    payload = {
        "task_type": "clients.celery.pdf_processing.transcribe_pdf_to_md",
        "task_parameters": {
            "pdf_file_content_base64": pdf_content_base64,
            "original_filename": original_filename,
            "task_options": task_options
        }
    }
    
    try:
        logger.info(f"正在提交PDF转Markdown任务，文件: {original_filename}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"提交任务失败: {str(e)}")
        raise

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
            progress = status_response["progress"]
            logger.info(f"任务进度: {progress['progress']}% - {progress['status']}")
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