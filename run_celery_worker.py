"""
Celery Worker启动脚本
配置并启动Celery Worker处理异步任务
"""

import os
import platform

# 解决Windows环境下Celery的兼容性问题
if platform.system() == "Windows":
    os.environ['FORKED_BY_MULTIPROCESSING'] = '1'

import argparse
import logging
from clients.celery import celery_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动Celery Worker')
    parser.add_argument(
        '--concurrency', 
        type=int, 
        default=4,
        help='Worker并发数量'
    )
    parser.add_argument(
        '--loglevel', 
        type=str, 
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='日志级别'
    )
    parser.add_argument(
        '--queues', 
        type=str, 
        default='default',
        help='处理的队列，用逗号分隔多个队列'
    )
    parser.add_argument(
        '--events',
        action='store_true',
        help='启用事件通知'
    )
    return parser.parse_args()

def main():
    """主入口函数"""
    args = parse_args()
    
    # 构建Celery Worker命令参数
    worker_args = [
        'worker',
        f'--concurrency={args.concurrency}',
        f'--loglevel={args.loglevel}',
        f'--queues={args.queues}'
    ]
    
    if args.events:
        worker_args.append('--events')
    
    # 设置环境变量
    os.environ['CELERY_WORKER_RUNNING'] = 'true'
    
    # 打印启动信息
    logger.info(f"启动Celery Worker，队列: {args.queues}，并发数: {args.concurrency}")
    
    # 启动Celery Worker
    celery_app.worker_main(worker_args)

if __name__ == "__main__":
    main() 