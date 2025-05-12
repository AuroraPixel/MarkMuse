"""
数据库感知的Celery任务基类
提供自动将任务状态同步到数据库的功能
"""

import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
from celery import Task
from celery.exceptions import Ignore, Retry
from celery.states import SUCCESS, FAILURE, RETRY, PENDING, STARTED, REVOKED
from celery.utils.log import get_task_logger

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# 导入数据库相关组件
from config.api_config import SessionLocal
from clients.db.crud import (
    create_task_log, 
    update_task_log_on_start, 
    update_task_log_status,
    update_task_log_on_completion,
    get_task_log
)

# 设置任务专用日志记录器
logger = get_task_logger(__name__)

class DatabaseAwareTask(Task):
    """
    数据库感知的任务基类
    
    自动将任务状态同步到数据库的TaskAuditLog表
    继承此类的任务将自动记录执行状态、结果和错误信息
    """
    # 任务属性
    abstract = True  # 标记为抽象类，不会被注册为可执行任务
    max_retries = 3  # 最大重试次数
    autoretry_for = (Exception,)  # 自动重试的异常类型
    retry_backoff = True  # 使用指数退避策略
    retry_backoff_max = 600  # 最大退避时间10分钟
    retry_jitter = True  # 添加随机抖动
    time_limit = 3600  # 默认任务超时时间（1小时）
    track_progress = True  # 是否跟踪任务进度
    
    def __init__(self):
        """初始化任务"""
        super().__init__()
        self._db = None
        self.progress = 0  # 进度（0-100）
        self.status_message = "已初始化"
    
    def get_db_session(self) -> Session:
        """
        获取数据库会话
        
        返回:
        - Session: SQLAlchemy会话实例
        """
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def close_db_session(self):
        """关闭数据库会话"""
        if self._db is not None:
            self._db.close()
            self._db = None
    
    def update_progress(self, progress: int, message: str = "") -> None:
        """
        更新任务进度
        
        参数:
        - progress: 进度百分比（0-100）
        - message: 状态消息
        """
        # 保存进度和状态
        self.progress = max(0, min(progress, 100))  # 确保在0-100范围内
        if message:
            self.status_message = message
        
        # 更新Celery任务状态
        if self.track_progress:
            progress_data = {
                'progress': self.progress,
                'status': self.status_message,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.update_state(state='PROGRESS', meta=progress_data)
            
            # 更新数据库中的任务状态
            try:
                db = self.get_db_session()
                update_task_log_status(
                    db=db, 
                    celery_task_id=self.request.id, 
                    new_status='PROGRESS',
                    progress_info=progress_data
                )
            except Exception as e:
                logger.warning(f"更新任务进度到数据库时出错: {e}")
            finally:
                self.close_db_session()
        
        # 记录日志
        logger.debug(f"任务进度: {self.progress}% - {self.status_message}")
    
    def __call__(self, *args, **kwargs):
        """
        任务执行入口
        
        在任务实际执行前，更新数据库中的任务状态为STARTED
        """
        try:
            # 更新任务状态为STARTED
            db = self.get_db_session()
            update_task_log_on_start(
                db=db, 
                celery_task_id=self.request.id,
                started_at=datetime.utcnow(),
                worker_name=self.request.hostname,
                retry_count=self.request.retries
            )
        except Exception as e:
            logger.warning(f"更新任务开始状态到数据库时出错: {e}")
        finally:
            self.close_db_session()
        
        # 调用父类方法执行实际任务
        return super().__call__(*args, **kwargs)
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        任务执行完成后的回调
        
        参数:
        - status: 任务状态（SUCCESS, FAILURE等）
        - retval: 任务返回值或异常对象
        - task_id: 任务ID
        - args: 任务位置参数
        - kwargs: 任务关键字参数
        - einfo: 异常信息（如果任务失败）
        """
        try:
            db = self.get_db_session()
            
            # 根据任务状态更新数据库
            if status == SUCCESS:
                # 任务成功完成
                update_task_log_on_completion(
                    db=db,
                    celery_task_id=task_id,
                    final_status=SUCCESS,
                    completed_at=datetime.utcnow(),
                    result_data=retval
                )
                logger.info(f"任务成功完成: {self.name}[{task_id}]")
            
            elif status == FAILURE:
                # 任务失败
                error_message = str(retval) if retval else "未知错误"
                traceback_info = str(einfo) if einfo else None
                
                update_task_log_on_completion(
                    db=db,
                    celery_task_id=task_id,
                    final_status=FAILURE,
                    completed_at=datetime.utcnow(),
                    error_message=error_message,
                    traceback_info=traceback_info
                )
                logger.error(f"任务执行失败: {self.name}[{task_id}] - {error_message}")
                
            else:
                # 其他状态（REVOKED等）
                update_task_log_status(
                    db=db,
                    celery_task_id=task_id,
                    new_status=status
                )
                logger.info(f"任务状态变更: {self.name}[{task_id}] - {status}")
                
        except Exception as db_exc:
            logger.error(f"任务完成后更新数据库时出错: {db_exc}")
        finally:
            self.close_db_session()
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        任务失败处理回调
        
        参数:
        - exc: 异常对象
        - task_id: 任务ID
        - args: 任务位置参数
        - kwargs: 任务关键字参数
        - einfo: 异常信息
        
        注意: 此方法可能与after_return有重叠，但Celery会在不同场景下触发不同的回调
        """
        # 主要失败处理逻辑已移至after_return方法
        # 此处可以添加额外的失败处理逻辑
        logger.error(f"任务失败回调: {self.name}[{task_id}] - {str(exc)}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        任务重试处理回调
        
        参数:
        - exc: 导致重试的异常对象
        - task_id: 任务ID
        - args: 任务位置参数
        - kwargs: 任务关键字参数
        - einfo: 异常信息
        """
        try:
            db = self.get_db_session()
            
            # 更新任务状态为RETRY，并递增重试计数
            update_task_log_status(
                db=db,
                celery_task_id=task_id,
                new_status=RETRY
            )
            
            # 获取当前任务日志并手动更新重试计数
            task_log = get_task_log(db, task_id)
            if task_log:
                retry_count = self.request.retries
                task_log.retry_count = retry_count
                db.commit()
                
            logger.warning(f"任务重试: {self.name}[{task_id}] - 尝试: {self.request.retries}/{self.max_retries}")
            
        except Exception as db_exc:
            logger.error(f"更新任务重试状态到数据库时出错: {db_exc}")
        finally:
            self.close_db_session()

# 导出任务类
__all__ = ['DatabaseAwareTask'] 