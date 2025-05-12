#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务队列API测试脚本
提供API的基本功能测试
"""

import os
import sys
import time
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
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

def submit_task(task_type: str, task_parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    提交任务
    
    参数:
    - task_type: 任务类型（Celery任务名称）
    - task_parameters: 任务参数
    
    返回:
    - Dict[str, Any]: API响应
    """
    url = f"{API_BASE_URL}/tasks/submit"
    payload = {
        "task_type": task_type,
        "task_parameters": task_parameters
    }
    
    try:
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

def get_task_list(page: int = 1, page_size: int = 10, task_type: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    """
    获取任务列表
    
    参数:
    - page: 页码
    - page_size: 每页数量
    - task_type: 任务类型（可选）
    - status: 任务状态（可选）
    
    返回:
    - Dict[str, Any]: API响应
    """
    url = f"{API_BASE_URL}/tasks/"
    params = {
        "page": page,
        "page_size": page_size
    }
    
    if task_type:
        params["task_type"] = task_type
    if status:
        params["status"] = status
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise

def wait_for_task_completion(task_id: str, max_wait: int = 60, interval: int = 2) -> Dict[str, Any]:
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
            return status_response
        
        # 等待一段时间后再次检查
        time.sleep(interval)
        elapsed = time.time() - start_time
    
    logger.warning(f"等待任务完成超时: {task_id}")
    return get_task_status(task_id)

def test_document_processing():
    """测试文档处理任务"""
    task_type = "clients.celery.example_tasks.process_document"
    task_parameters = {
        "document_id": "doc-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "options": {
            "format": "pdf",
            "quality": "high"
        }
    }
    
    logger.info("提交文档处理任务")
    response = submit_task(task_type, task_parameters)
    
    task_id = response.get("task_id")
    logger.info(f"任务已提交，ID: {task_id}")
    
    # 等待任务完成
    final_status = wait_for_task_completion(task_id)
    
    # 打印最终结果
    logger.info("任务最终状态:")
    pprint(final_status)
    
    return task_id

def test_report_generation():
    """测试报告生成任务"""
    task_type = "clients.celery.example_tasks.generate_report"
    task_parameters = {
        "report_type": "monthly_summary",
        "parameters": {
            "month": datetime.now().strftime("%Y-%m"),
            "department": "研发部",
            "include_charts": True
        }
    }
    
    logger.info("提交报告生成任务")
    response = submit_task(task_type, task_parameters)
    
    task_id = response.get("task_id")
    logger.info(f"任务已提交，ID: {task_id}")
    
    # 等待任务完成
    final_status = wait_for_task_completion(task_id)
    
    # 打印最终结果
    logger.info("任务最终状态:")
    pprint(final_status)
    
    return task_id

def test_data_processing():
    """测试数据处理链任务"""
    task_type = "clients.celery.example_tasks.data_processing_chain"
    
    # 生成随机测试数据
    data_items = []
    for i in range(10):
        data_items.append({
            "id": f"item-{i+1}",
            "value": i * 10,
            "name": f"测试项目 {i+1}",
            "timestamp": datetime.now().isoformat()
        })
    
    task_parameters = {
        "data_items": data_items
    }
    
    logger.info("提交数据处理链任务")
    response = submit_task(task_type, task_parameters)
    
    task_id = response.get("task_id")
    logger.info(f"任务已提交，ID: {task_id}")
    
    # 等待任务完成
    final_status = wait_for_task_completion(task_id)
    
    # 打印最终结果
    logger.info("任务最终状态:")
    pprint(final_status)
    
    return task_id

def test_query_tasks():
    """测试查询任务列表"""
    logger.info("查询任务列表")
    task_list = get_task_list(page=1, page_size=5)
    
    logger.info(f"共找到 {task_list.get('total_count', 0)} 个任务")
    for i, task in enumerate(task_list.get("tasks", [])):
        logger.info(f"任务 {i+1}: ID={task.get('task_id')} 类型={task.get('task_type')} 状态={task.get('status')}")
    
    return task_list

def run_task_api_tests():
    """运行任务API测试"""
    try:
        # 测试任务提交和执行
        logger.info("=== 测试文档处理任务 ===")
        doc_task_id = test_document_processing()
        
        logger.info("\n=== 测试报告生成任务 ===")
        report_task_id = test_report_generation()
        
        logger.info("\n=== 测试数据处理链任务 ===")
        data_task_id = test_data_processing()
        
        # 等待一段时间，确保任务都有足够时间完成
        time.sleep(2)
        
        # 测试任务列表查询
        logger.info("\n=== 测试任务列表查询 ===")
        test_query_tasks()
        
        logger.info("\n测试完成")
        return True
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        return False

def main():
    """主入口函数"""
    success = run_task_api_tests()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 