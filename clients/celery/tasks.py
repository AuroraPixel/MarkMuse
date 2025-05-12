"""
Celery任务定义
提供通用任务基类和任务注册功能
"""

import logging
import functools
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union, TypeVar, cast

from celery import Task, current_task, shared_task
from celery.utils.log import get_task_logger
from celery.exceptions import Ignore, Retry

from .app import celery_app
from .base_tasks import DatabaseAwareTask

# 设置任务专用日志记录器
logger = get_task_logger(__name__)

# 定义任务函数类型
TaskFunc = TypeVar('TaskFunc', bound=Callable[..., Any])


class TaskError(Exception):
    """任务执行异常"""
    pass


class BaseTask(Task):
    """
    任务基类，提供通用的任务执行流程和错误处理
    
    继承此类可以实现自定义任务类型，重写run方法
    """
    # 任务属性
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
        self.progress = 0  # 进度（0-100）
        self.status_message = "已初始化"
        self.result_data = None
    
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
        
        # 如果当前任务存在且支持进度跟踪
        if current_task and self.track_progress:
            current_task.update_state(
                state='PROGRESS',
                meta={
                    'progress': self.progress,
                    'status': self.status_message
                }
            )
        
        # 记录日志
        logger.debug(f"任务进度: {self.progress}% - {self.status_message}")
    
    def run(self, *args, **kwargs) -> Any:
        """
        任务执行入口（由子类实现）
        
        参数:
        - args, kwargs: 任务参数
        
        返回:
        - Any: 任务执行结果
        """
        raise NotImplementedError("子类必须实现run方法")
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """
        任务成功处理回调
        
        参数:
        - retval: 任务返回值
        - task_id: 任务ID
        - args: 任务位置参数
        - kwargs: 任务关键字参数
        """
        logger.info(f"任务成功完成: {self.name}[{task_id}]")
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo) -> None:
        """
        任务失败处理回调
        
        参数:
        - exc: 异常对象
        - task_id: 任务ID
        - args: 任务位置参数
        - kwargs: 任务关键字参数
        - einfo: 异常信息
        """
        logger.error(f"任务执行失败: {self.name}[{task_id}] - {str(exc)}")
    
    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo) -> None:
        """
        任务重试处理回调
        
        参数:
        - exc: 异常对象
        - task_id: 任务ID
        - args: 任务位置参数
        - kwargs: 任务关键字参数
        - einfo: 异常信息
        """
        logger.warning(f"任务重试: {self.name}[{task_id}] - 尝试: {self.request.retries}/{self.max_retries}")


class AsyncTask(BaseTask):
    """
    异步任务基类
    
    提供通用的异步任务执行框架，包含预处理、执行和后处理步骤
    """
    
    def preprocess(self, *args, **kwargs) -> Dict[str, Any]:
        """
        任务预处理，处理输入参数
        
        参数:
        - args, kwargs: 任务参数
        
        返回:
        - Dict[str, Any]: 预处理结果
        """
        # 默认实现，可由子类重写
        return {'args': args, 'kwargs': kwargs}
    
    def execute(self, data: Dict[str, Any]) -> Any:
        """
        执行任务核心逻辑
        
        参数:
        - data: 预处理的数据
        
        返回:
        - Any: 执行结果
        """
        # 必须由子类实现
        raise NotImplementedError("子类必须实现execute方法")
    
    def postprocess(self, result: Any) -> Any:
        """
        任务后处理，处理执行结果
        
        参数:
        - result: 执行结果
        
        返回:
        - Any: 后处理结果
        """
        # 默认实现，可由子类重写
        return result
    
    def run(self, *args, **kwargs) -> Any:
        """
        异步任务执行入口
        
        参数:
        - args, kwargs: 任务参数
        
        返回:
        - Any: 任务执行结果
        """
        self.update_progress(0, "任务开始")
        start_time = time.time()
        
        try:
            # 预处理
            self.update_progress(10, "预处理阶段")
            processed_data = self.preprocess(*args, **kwargs)
            
            # 执行核心逻辑
            self.update_progress(30, "执行阶段")
            result = self.execute(processed_data)
            
            # 后处理
            self.update_progress(80, "后处理阶段")
            final_result = self.postprocess(result)
            
            # 完成
            self.update_progress(100, "任务完成")
            
            # 记录执行时间
            elapsed = time.time() - start_time
            logger.info(f"任务耗时: {elapsed:.2f}秒")
            
            return final_result
            
        except Exception as e:
            # 记录异常
            self.update_progress(0, f"任务失败: {str(e)}")
            logger.error(f"任务执行出错: {str(e)}")
            logger.error(traceback.format_exc())
            raise


class PeriodicTask(AsyncTask):
    """
    定期任务基类
    
    提供基于Celery beat的定期执行任务框架
    """
    
    # 定期任务调度配置
    run_every = None  # 例如：timedelta(hours=1)
    
    @classmethod
    def register_schedule(cls, app=None):
        """
        注册定期任务调度
        
        参数:
        - app: Celery应用实例
        
        返回:
        - dict: Celery beat调度配置
        """
        if app is None:
            app = celery_app
            
        if cls.run_every is None:
            logger.warning(f"任务{cls.__name__}未指定run_every，无法注册调度")
            return {}
            
        # 注册定期任务调度
        schedule_name = f'{cls.__name__}_schedule'
        schedule_entry = {
            'task': cls.name,
            'schedule': cls.run_every,
            'args': (),
            'kwargs': {},
            'options': {
                'expires': 3600  # 默认过期时间1小时
            }
        }
        
        # 更新Celery beat调度
        app.conf.beat_schedule = getattr(app.conf, 'beat_schedule', {})
        app.conf.beat_schedule[schedule_name] = schedule_entry
        
        logger.info(f"已注册定期任务: {cls.name}, 间隔: {cls.run_every}")
        return {schedule_name: schedule_entry}


def register_task(base=None, name=None, **options):
    """
    任务注册装饰器
    
    参数:
    - base: 任务基类，默认为BaseTask
    - name: 任务名称，默认为函数全名
    - options: 其他任务选项
    
    返回:
    - function: 装饰器函数
    """
    def decorator(func):
        # 使用自定义基类和选项注册任务
        base_cls = base or BaseTask
        task_name = name or f"{func.__module__}.{func.__name__}"
        
        # 应用装饰器
        return celery_app.task(
            base=base_cls,
            name=task_name,
            bind=True,
            **options
        )(func)
    
    return decorator


@shared_task(base=AsyncTask, bind=True)
def example_task(self, task_name: str, delay: int = 5) -> Dict[str, Any]:
    """
    示例任务：模拟长时间运行的处理过程
    
    参数:
    - task_name: 任务名称
    - delay: 模拟处理延迟（秒）
    
    返回:
    - Dict[str, Any]: 任务结果
    """
    logger.info(f"开始执行示例任务: {task_name}, 延迟: {delay}秒")
    
    # 更新初始进度
    self.update_progress(0, "任务开始")
    
    # 模拟多步骤处理过程
    steps = 5
    for i in range(1, steps + 1):
        # 计算当前进度
        progress = i * (100 // steps)
        # 更新进度
        self.update_progress(progress, f"处理步骤 {i}/{steps}")
        # 模拟处理时间
        time.sleep(delay / steps)
    
    # 完成任务
    self.update_progress(100, "任务完成")
    
    # 返回结果
    return {
        "task_name": task_name,
        "status": "成功",
        "details": {
            "steps_completed": steps,
            "total_delay": delay
        }
    }


@shared_task(base=DatabaseAwareTask, bind=True)
def db_aware_task(self, task_name: str, delay: int = 5, fail: bool = False) -> Dict[str, Any]:
    """
    数据库感知的示例任务，将状态同步到数据库
    
    参数:
    - task_name: 任务名称
    - delay: 模拟处理延迟（秒）
    - fail: 是否模拟失败
    
    返回:
    - Dict[str, Any]: 任务结果
    """
    logger.info(f"开始执行数据库感知任务: {task_name}, 延迟: {delay}秒, 失败模式: {fail}")
    
    # 模拟多步骤处理过程
    steps = 5
    for i in range(1, steps + 1):
        # 计算当前进度
        progress = i * (100 // steps)
        # 更新进度（会自动同步到数据库）
        self.update_progress(progress, f"处理步骤 {i}/{steps}")
        # 模拟处理时间
        time.sleep(delay / steps)
        
        # 如果配置为失败模式，在中间步骤失败
        if fail and i == 3:
            raise TaskError(f"任务 {task_name} 在步骤 {i} 模拟失败")
    
    # 完成任务
    self.update_progress(100, "任务完成")
    
    # 返回结果
    return {
        "task_name": task_name,
        "status": "成功",
        "details": {
            "steps_completed": steps,
            "total_delay": delay
        }
    } 