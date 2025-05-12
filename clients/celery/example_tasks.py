"""
示例任务模块
提供用于测试的任务示例
"""

import time
import logging
import random
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger

from .base_tasks import DatabaseAwareTask

# 设置任务专用日志记录器
logger = get_task_logger(__name__)

@shared_task(bind=True, base=DatabaseAwareTask)
def process_document(
    self, 
    document_id: str, 
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    示例任务：模拟文档处理
    
    参数:
    - document_id: 文档ID
    - options: 处理选项
    
    返回:
    - Dict[str, Any]: 处理结果
    """
    logger.info(f"开始处理文档: {document_id}")
    total_pages = random.randint(5, 20)
    processing_time = 0.5
    
    # 初始化进度
    self.update_progress(0, f"开始处理文档 {document_id}，共 {total_pages} 页")
    
    # 模拟文档处理过程
    for page in range(1, total_pages + 1):
        # 随机处理时间，模拟不同页面处理耗时不同
        page_time = random.uniform(0.2, 0.8)
        time.sleep(page_time)
        processing_time += page_time
        
        # 更新进度
        progress = int((page / total_pages) * 100)
        self.update_progress(progress, f"处理页面 {page}/{total_pages}")
        
        # 随机模拟失败（概率约5%）
        if random.random() < 0.05:
            raise Exception(f"处理页面 {page} 时出错：模拟随机失败")
    
    # 处理完成
    self.update_progress(100, "文档处理完成")
    
    # 返回结果
    return {
        "document_id": document_id,
        "status": "completed",
        "pages_processed": total_pages,
        "processing_time": round(processing_time, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "options": options or {}
    }

@shared_task(bind=True, base=DatabaseAwareTask)
def generate_report(
    self, 
    report_type: str, 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    示例任务：模拟报告生成
    
    参数:
    - report_type: 报告类型
    - parameters: 报告参数
    
    返回:
    - Dict[str, Any]: 生成的报告
    """
    logger.info(f"开始生成报告 - 类型: {report_type}")
    
    # 初始化进度
    self.update_progress(0, f"开始生成 {report_type} 报告")
    
    # 模拟数据收集阶段
    self.update_progress(10, "收集报告数据")
    time.sleep(random.uniform(1.0, 2.0))
    
    # 模拟数据处理阶段
    self.update_progress(30, "处理报告数据")
    time.sleep(random.uniform(0.5, 1.5))
    
    # 模拟报告生成阶段
    self.update_progress(60, "生成报告内容")
    time.sleep(random.uniform(1.0, 2.0))
    
    # 模拟格式化阶段
    self.update_progress(80, "格式化报告")
    time.sleep(random.uniform(0.5, 1.0))
    
    # 生成随机报告数据
    report_data = {
        "title": f"{report_type.capitalize()} 报告",
        "generated_at": datetime.utcnow().isoformat(),
        "parameters": parameters,
        "sections": [
            {"name": "摘要", "content": "这是报告摘要部分"},
            {"name": "详情", "content": "这是报告详情部分"},
            {"name": "结论", "content": "这是报告结论部分"}
        ],
        "metrics": {
            "value_1": random.randint(100, 1000),
            "value_2": random.randint(1000, 10000),
            "value_3": random.uniform(0.1, 0.9)
        }
    }
    
    # 完成
    self.update_progress(100, "报告生成完成")
    
    return {
        "report_type": report_type,
        "status": "completed",
        "report_data": report_data,
        "parameters": parameters
    }

@shared_task(bind=True, base=DatabaseAwareTask)
def data_processing_chain(self, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    示例任务：模拟数据处理链
    
    参数:
    - data_items: 要处理的数据项列表
    
    返回:
    - Dict[str, Any]: 处理结果
    """
    total_items = len(data_items)
    logger.info(f"开始数据处理链，共 {total_items} 项")
    
    # 初始化进度
    self.update_progress(0, f"准备处理 {total_items} 项数据")
    
    # 处理结果
    results = []
    failures = []
    
    # 处理每个数据项
    for i, item in enumerate(data_items):
        try:
            # 更新进度
            item_progress = int((i / total_items) * 100)
            self.update_progress(item_progress, f"处理项目 {i+1}/{total_items}")
            
            # 模拟处理时间
            time.sleep(random.uniform(0.2, 0.5))
            
            # 模拟处理逻辑
            processed_item = {
                "id": item.get("id") or i,
                "original_data": item,
                "processed_at": datetime.utcnow().isoformat(),
                "processed_value": item.get("value", 0) * random.randint(2, 5)
            }
            
            # 添加到结果
            results.append(processed_item)
            
        except Exception as e:
            # 记录失败
            failures.append({
                "item": item,
                "error": str(e)
            })
            logger.error(f"处理数据项 {i+1} 失败: {str(e)}")
    
    # 完成
    self.update_progress(100, "数据处理链完成")
    
    # 返回结果
    return {
        "total_items": total_items,
        "successful_items": len(results),
        "failed_items": len(failures),
        "results": results,
        "failures": failures,
        "completed_at": datetime.utcnow().isoformat()
    }

# 导出任务列表
__all__ = ['process_document', 'generate_report', 'data_processing_chain'] 