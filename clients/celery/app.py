"""
Celery应用配置
提供Celery应用实例和配置功能
"""

import logging
import os
from typing import Dict, Any, Optional

from celery import Celery
from celery.signals import task_failure, task_success, task_revoked, worker_ready
from config import APIConfig, load_api_config

logger = logging.getLogger(__name__)

# 创建Celery应用实例
celery_app = Celery('markmuse')

# 默认配置
default_config = {
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 3600,
    'worker_concurrency': 4,
    'worker_prefetch_multiplier': 4,
    'worker_max_tasks_per_child': 1000,
    'broker_pool_limit': 10,
}


def configure_celery(app: Celery, config: Optional[APIConfig] = None, **kwargs) -> Celery:
    """
    配置Celery应用
    
    参数:
    - app: Celery应用实例
    - config: API配置对象，包含Celery配置信息
    - kwargs: 其他配置参数，将覆盖默认配置
    
    返回:
    - Celery: 配置后的Celery应用实例
    """
    try:
        # 使用传入的配置或加载默认配置
        api_config = config or load_api_config()
        
        # 获取broker_url
        broker_url = kwargs.get('broker_url') or api_config.celery_broker_url or api_config.redis_url
        if not broker_url:
            # 如果未设置broker_url，则使用Redis配置构建
            password_part = f":{api_config.redis_password}@" if api_config.redis_password else ""
            protocol = "rediss" if api_config.redis_ssl else "redis"
            broker_url = f"{protocol}://{password_part}{api_config.redis_host}:{api_config.redis_port}/{api_config.redis_db}"
        
        # 获取result_backend
        result_backend = kwargs.get('result_backend') or api_config.celery_result_backend
        if not result_backend:
            # 如果未设置result_backend，优先使用同一个Redis作为结果后端
            result_backend = broker_url
        
        # 检查是否为测试环境（通过环境变量）
        is_test_env = os.environ.get('CELERY_TASK_ALWAYS_EAGER', '').lower() in ('true', '1', 'yes')
        
        # 构建Celery配置
        celery_config = {
            'broker_url': broker_url,
            'result_backend': result_backend,
        }
        
        # 测试环境特殊配置
        if is_test_env:
            celery_config['task_always_eager'] = True
            celery_config['task_eager_propagates'] = True
            logger.info("Celery配置为测试模式（eager执行）")
        
        # 合并默认配置
        celery_config.update(default_config)
        
        # 从API配置中获取Celery配置
        if hasattr(api_config, 'celery_task_serializer'):
            celery_config['task_serializer'] = api_config.celery_task_serializer
        if hasattr(api_config, 'celery_result_serializer'):
            celery_config['result_serializer'] = api_config.celery_result_serializer
        if hasattr(api_config, 'celery_accept_content'):
            celery_config['accept_content'] = [api_config.celery_accept_content]
        if hasattr(api_config, 'celery_timezone'):
            celery_config['timezone'] = api_config.celery_timezone
        if hasattr(api_config, 'celery_enable_utc'):
            celery_config['enable_utc'] = api_config.celery_enable_utc
        if hasattr(api_config, 'celery_task_track_started'):
            celery_config['task_track_started'] = api_config.celery_task_track_started
        if hasattr(api_config, 'celery_task_time_limit'):
            celery_config['task_time_limit'] = api_config.celery_task_time_limit
        if hasattr(api_config, 'celery_worker_concurrency'):
            celery_config['worker_concurrency'] = api_config.celery_worker_concurrency
        
        # 应用额外的自定义配置（优先级最高）
        celery_config.update(kwargs)
        
        # 配置Celery应用
        app.conf.update(celery_config)
        
        # 设置任务默认路由
        app.conf.task_default_queue = 'default'
        
        # 注册任务
        app.autodiscover_tasks(['clients.celery.tasks', 'clients.celery.example_tasks'])
        
        # 记录配置完成
        broker_display = broker_url.split('@')[-1] if '@' in broker_url else broker_url
        logger.info(f"Celery配置完成，Broker: {broker_display}")
        return app
    
    except Exception as e:
        logger.error(f"Celery配置失败: {str(e)}")
        # 使用最小配置
        app.conf.broker_url = 'redis://localhost:6379/0'
        app.conf.result_backend = 'redis://localhost:6379/0'
        
        # 测试环境特殊配置
        if os.environ.get('CELERY_TASK_ALWAYS_EAGER', '').lower() in ('true', '1', 'yes'):
            app.conf.task_always_eager = True
            app.conf.task_eager_propagates = True
        
        logger.warning("使用最小Celery配置（本地Redis）")
        return app


# 任务相关信号处理

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, 
                       args=None, kwargs=None, traceback=None, einfo=None, **kw):
    """记录任务失败信息"""
    logger.error(f"任务失败: {sender.name}[{task_id}] - {str(exception)}")


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """记录任务成功信息"""
    try:
        # 避免记录大量结果数据
        result_log = str(result)[:100] + '...' if result and len(str(result)) > 100 else result
        logger.info(f"任务成功: {sender.name}[{kwargs.get('task_id')}] - 结果: {result_log}")
    except Exception as e:
        logger.warning(f"记录任务成功信息失败: {str(e)}")


@task_revoked.connect
def task_revoked_handler(sender=None, request=None, terminated=None, signum=None, **kwargs):
    """记录任务撤销信息"""
    logger.warning(f"任务被撤销: {request.task}[{request.id}]")


@worker_ready.connect
def worker_ready_handler(**kwargs):
    """记录worker就绪信息"""
    logger.info("Celery worker就绪")


# 使用默认配置初始化Celery
configure_celery(celery_app)

# 导出实例
__all__ = ['celery_app', 'configure_celery'] 