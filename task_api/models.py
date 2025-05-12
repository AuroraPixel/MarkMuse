"""
API模型定义
使用Pydantic定义请求和响应模型
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"  # 等待执行
    RECEIVED = "RECEIVED"  # 已接收
    STARTED = "STARTED"  # 已开始执行
    PROGRESS = "PROGRESS"  # 执行中
    RETRY = "RETRY"  # 重试中
    SUCCESS = "SUCCESS"  # 已成功完成
    FAILURE = "FAILURE"  # 执行失败
    REVOKED = "REVOKED"  # 已撤销


class TaskProgress(BaseModel):
    """任务进度模型"""
    progress: int = Field(0, ge=0, le=100, description="进度百分比（0-100）")
    status: str = Field("", description="进度状态描述")
    timestamp: Optional[datetime] = Field(None, description="进度更新时间")


class TaskSubmitRequest(BaseModel):
    """
    任务提交请求模型
    
    用于API接收任务提交请求
    """
    task_type: str = Field(..., description="任务类型（Celery任务名称）")
    task_parameters: Optional[Dict[str, Any]] = Field(None, description="任务参数，将作为关键字参数传递给任务")
    priority: Optional[int] = Field(None, ge=0, le=9, description="任务优先级（0-9，越高越优先）")
    
    # 可选参数
    eta: Optional[datetime] = Field(None, description="任务计划执行时间（不早于此时间）")
    expires: Optional[Union[datetime, int]] = Field(None, description="任务过期时间（datetime或秒数）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_type": "clients.celery.tasks.db_aware_task",
                "task_parameters": {
                    "task_name": "测试任务",
                    "delay": 2
                },
                "priority": 5
            }
        }


class TaskSubmitResponse(BaseModel):
    """
    任务提交响应模型
    
    API提交任务后的响应
    """
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(TaskStatus.PENDING, description="任务状态")
    message: str = Field("任务已成功提交", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "8f8e3d3a-7b1e-4fee-b1cb-7d8a9ca0e369",
                "status": "PENDING",
                "message": "任务已成功提交"
            }
        }


class TaskStatusResponse(BaseModel):
    """
    任务状态响应模型
    
    用于API返回任务状态查询结果
    """
    task_id: str = Field(..., description="任务ID")
    task_type: Optional[str] = Field(None, description="任务类型")
    status: TaskStatus = Field(..., description="任务状态")
    
    # 时间信息
    submitted_at: Optional[datetime] = Field(None, description="任务提交时间")
    started_at: Optional[datetime] = Field(None, description="任务开始时间")
    completed_at: Optional[datetime] = Field(None, description="任务完成时间")
    
    # 进度信息
    progress: Optional[TaskProgress] = Field(None, description="任务进度")
    
    # 结果信息
    result: Optional[Any] = Field(None, description="任务结果（如果已完成）")
    error_message: Optional[str] = Field(None, description="错误信息（如果失败）")
    traceback: Optional[str] = Field(None, description="异常堆栈（如果失败）")
    
    # 额外信息
    retry_count: Optional[int] = Field(None, description="重试次数")
    worker_name: Optional[str] = Field(None, description="执行任务的worker名称")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "8f8e3d3a-7b1e-4fee-b1cb-7d8a9ca0e369",
                "task_type": "clients.celery.tasks.db_aware_task",
                "status": "SUCCESS",
                "submitted_at": "2023-11-05T12:00:00Z",
                "started_at": "2023-11-05T12:00:05Z",
                "completed_at": "2023-11-05T12:00:15Z",
                "progress": {
                    "progress": 100,
                    "status": "任务完成",
                    "timestamp": "2023-11-05T12:00:15Z"
                },
                "result": {
                    "task_name": "测试任务",
                    "status": "成功",
                    "details": {
                        "steps_completed": 5,
                        "total_delay": 2
                    }
                },
                "retry_count": 0,
                "worker_name": "celery@worker1"
            }
        }


class TaskListResponse(BaseModel):
    """
    任务列表响应模型
    
    用于API返回任务列表查询结果
    """
    tasks: List[TaskStatusResponse] = Field(..., description="任务列表")
    total_count: int = Field(..., description="任务总数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(..., description="每页数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "task_id": "8f8e3d3a-7b1e-4fee-b1cb-7d8a9ca0e369",
                        "task_type": "clients.celery.tasks.db_aware_task",
                        "status": "SUCCESS",
                        "submitted_at": "2023-11-05T12:00:00Z",
                        "completed_at": "2023-11-05T12:00:15Z"
                    }
                ],
                "total_count": 1,
                "page": 1,
                "page_size": 10
            }
        } 