"""
数据库模型定义
使用 SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class ExampleTable(Base):
    """
    示例表模型
    演示基本的数据模型定义
    """
    __tablename__ = "example_table"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<ExampleTable(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        """
        将模型转换为字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None, 
            "active": self.active
        }

class TaskAuditLog(Base):
    """
    任务审计日志模型
    用于记录任务执行的详细信息，提供持久化存储
    """
    __tablename__ = "task_audit_log"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    celery_task_id = Column(String(50), unique=True, index=True, nullable=False)
    task_type = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, default='PENDING', index=True)
    # 尝试使用PostgreSQL的JSONB类型，如果不支持则回退到通用JSON类型
    try:
        task_parameters = Column(JSONB, nullable=True)
        result_data = Column(JSONB, nullable=True)
    except Exception:
        task_parameters = Column(JSON, nullable=True)
        result_data = Column(JSON, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    traceback_info = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    worker_name = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<TaskAuditLog(id={self.id}, celery_task_id='{self.celery_task_id}', task_type='{self.task_type}', status='{self.status}')>"
    
    def to_dict(self):
        """
        将模型转换为字典
        """
        return {
            "id": self.id,
            "celery_task_id": self.celery_task_id,
            "task_type": self.task_type,
            "status": self.status,
            "task_parameters": self.task_parameters,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "traceback_info": self.traceback_info,
            "retry_count": self.retry_count,
            "worker_name": self.worker_name
        } 