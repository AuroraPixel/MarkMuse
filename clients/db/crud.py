"""
数据库 CRUD 操作
包含各种模型的增删改查操作
"""

import logging
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .models import ExampleTable, TaskAuditLog

logger = logging.getLogger(__name__)

# ExampleTable 的 CRUD 操作

def create_example_item(db: Session, data: Dict[str, Any]) -> ExampleTable:
    """
    创建一个新的示例项
    
    参数:
    - db: 数据库会话
    - data: 包含字段值的字典
    
    返回:
    - ExampleTable: 创建的项
    """
    try:
        db_item = ExampleTable(**data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as e:
        db.rollback()
        logger.error(f"创建示例项时出错: {e}")
        raise

def get_example_item(db: Session, item_id: int) -> Optional[ExampleTable]:
    """
    通过 ID 获取示例项
    
    参数:
    - db: 数据库会话
    - item_id: 项目ID
    
    返回:
    - Optional[ExampleTable]: 找到的项或None
    """
    return db.query(ExampleTable).filter(ExampleTable.id == item_id).first()

def get_example_items(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = True
) -> List[ExampleTable]:
    """
    获取示例项列表
    
    参数:
    - db: 数据库会话
    - skip: 跳过的记录数
    - limit: 返回的记录数限制
    - active_only: 是否只返回活动状态的记录
    
    返回:
    - List[ExampleTable]: 示例项列表
    """
    query = db.query(ExampleTable)
    if active_only:
        query = query.filter(ExampleTable.active == True)
    return query.offset(skip).limit(limit).all()

def update_example_item(
    db: Session, 
    item_id: int, 
    data: Dict[str, Any]
) -> Optional[ExampleTable]:
    """
    更新示例项
    
    参数:
    - db: 数据库会话
    - item_id: 要更新的项目ID
    - data: 包含更新字段的字典
    
    返回:
    - Optional[ExampleTable]: 更新后的项或None（如果不存在）
    """
    try:
        db_item = get_example_item(db, item_id)
        if not db_item:
            return None
            
        for key, value in data.items():
            if hasattr(db_item, key):
                setattr(db_item, key, value)
        
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as e:
        db.rollback()
        logger.error(f"更新示例项时出错: {e}")
        raise

def delete_example_item(db: Session, item_id: int) -> bool:
    """
    删除示例项
    
    参数:
    - db: 数据库会话
    - item_id: 要删除的项目ID
    
    返回:
    - bool: 操作是否成功
    """
    try:
        db_item = get_example_item(db, item_id)
        if not db_item:
            return False
            
        db.delete(db_item)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"删除示例项时出错: {e}")
        raise

# TaskAuditLog 的 CRUD 操作

def create_task_log(
    db: Session, 
    celery_task_id: str, 
    task_type: str, 
    task_parameters: Optional[Dict[str, Any]] = None,
    submitted_at: Optional[datetime] = None
) -> TaskAuditLog:
    """
    创建一个新的任务审计日志
    
    参数:
    - db: 数据库会话
    - celery_task_id: Celery 任务ID
    - task_type: 任务类型（通常是任务名称）
    - task_parameters: 任务参数（可选）
    - submitted_at: 任务提交时间（可选，默认为当前时间）
    
    返回:
    - TaskAuditLog: 创建的任务日志
    """
    try:
        if submitted_at is None:
            submitted_at = datetime.utcnow()
            
        db_task = TaskAuditLog(
            celery_task_id=celery_task_id,
            task_type=task_type,
            status='PENDING',
            task_parameters=task_parameters,
            submitted_at=submitted_at
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"创建任务日志时出错: {e}")
        raise

def get_task_log(db: Session, celery_task_id: str) -> Optional[TaskAuditLog]:
    """
    通过 Celery 任务 ID 获取任务日志
    
    参数:
    - db: 数据库会话
    - celery_task_id: Celery 任务ID
    
    返回:
    - Optional[TaskAuditLog]: 找到的任务日志或None
    """
    return db.query(TaskAuditLog).filter(TaskAuditLog.celery_task_id == celery_task_id).first()

def update_task_log_on_start(
    db: Session, 
    celery_task_id: str, 
    started_at: Optional[datetime] = None,
    worker_name: Optional[str] = None,
    retry_count: int = 0
) -> Optional[TaskAuditLog]:
    """
    更新任务日志为开始状态
    
    参数:
    - db: 数据库会话
    - celery_task_id: Celery 任务ID
    - started_at: 任务开始时间（可选，默认为当前时间）
    - worker_name: 执行任务的 worker 名称
    - retry_count: 重试次数
    
    返回:
    - Optional[TaskAuditLog]: 更新后的任务日志或None
    """
    try:
        db_task = get_task_log(db, celery_task_id)
        if not db_task:
            logger.warning(f"未找到任务日志，celery_task_id: {celery_task_id}")
            return None
            
        if started_at is None:
            started_at = datetime.utcnow()
            
        db_task.status = 'STARTED'
        db_task.started_at = started_at
        db_task.worker_name = worker_name
        db_task.retry_count = retry_count
        
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"更新任务开始状态时出错: {e}")
        raise

def update_task_log_status(
    db: Session, 
    celery_task_id: str, 
    new_status: str,
    progress_info: Optional[Dict[str, Any]] = None
) -> Optional[TaskAuditLog]:
    """
    更新任务日志状态（中间状态，如 PROGRESS, RETRY）
    
    参数:
    - db: 数据库会话
    - celery_task_id: Celery 任务ID
    - new_status: 新状态
    - progress_info: 进度信息（可选）
    
    返回:
    - Optional[TaskAuditLog]: 更新后的任务日志或None
    """
    try:
        db_task = get_task_log(db, celery_task_id)
        if not db_task:
            logger.warning(f"未找到任务日志，celery_task_id: {celery_task_id}")
            return None
            
        db_task.status = new_status
        
        # 如果是重试状态，更新重试计数
        if new_status == 'RETRY':
            db_task.retry_count += 1
        
        # 如果有进度信息，可以考虑将其存储在 result_data 字段中
        if progress_info is not None:
            db_task.result_data = progress_info
        
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"更新任务状态时出错: {e}")
        raise

def update_task_log_on_completion(
    db: Session, 
    celery_task_id: str, 
    final_status: str,
    completed_at: Optional[datetime] = None,
    result_data: Optional[Any] = None,
    error_message: Optional[str] = None,
    traceback_info: Optional[str] = None
) -> Optional[TaskAuditLog]:
    """
    更新任务日志为完成状态（成功或失败）
    
    参数:
    - db: 数据库会话
    - celery_task_id: Celery 任务ID
    - final_status: 最终状态（SUCCESS, FAILURE, REVOKED）
    - completed_at: 任务完成时间（可选，默认为当前时间）
    - result_data: 任务结果数据（可选）
    - error_message: 错误信息（可选）
    - traceback_info: 异常堆栈（可选）
    
    返回:
    - Optional[TaskAuditLog]: 更新后的任务日志或None
    """
    try:
        db_task = get_task_log(db, celery_task_id)
        if not db_task:
            logger.warning(f"未找到任务日志，celery_task_id: {celery_task_id}")
            return None
            
        if completed_at is None:
            completed_at = datetime.utcnow()
            
        db_task.status = final_status
        db_task.completed_at = completed_at
        
        if final_status == 'SUCCESS' and result_data is not None:
            db_task.result_data = result_data
            
        if final_status == 'FAILURE':
            db_task.error_message = error_message
            db_task.traceback_info = traceback_info
        
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"更新任务完成状态时出错: {e}")
        raise

def get_task_logs(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[TaskAuditLog]:
    """
    获取任务日志列表，支持多种过滤条件
    
    参数:
    - db: 数据库会话
    - skip: 跳过的记录数
    - limit: 返回的记录数限制
    - task_type: 按任务类型过滤（可选）
    - status: 按状态过滤（可选）
    - start_date: 开始日期（可选，基于submitted_at）
    - end_date: 结束日期（可选，基于submitted_at）
    
    返回:
    - List[TaskAuditLog]: 任务日志列表
    """
    query = db.query(TaskAuditLog)
    
    # 应用过滤条件
    if task_type:
        query = query.filter(TaskAuditLog.task_type == task_type)
    if status:
        query = query.filter(TaskAuditLog.status == status)
    if start_date:
        query = query.filter(TaskAuditLog.submitted_at >= start_date)
    if end_date:
        query = query.filter(TaskAuditLog.submitted_at <= end_date)
    
    # 按提交时间逆序排序（最新的优先）
    query = query.order_by(TaskAuditLog.submitted_at.desc())
    
    return query.offset(skip).limit(limit).all() 