"""
Celery 客户端模块
提供异步任务队列管理功能
"""

from .app import celery_app, configure_celery
from .tasks import BaseTask, register_task
from .base_tasks import DatabaseAwareTask

__all__ = ['celery_app', 'configure_celery', 'BaseTask', 'register_task', 'DatabaseAwareTask'] 