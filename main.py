"""
统一启动脚本
使用线程同时启动 FastAPI 应用和 Celery Worker
"""

import os
import sys
import platform
import argparse
import logging
import threading
import subprocess
import signal

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动 FastAPI 应用和 Celery Worker')
    
    # API 服务参数
    parser.add_argument(
        '--api-host', 
        type=str, 
        default='0.0.0.0',
        help='API 服务监听地址'
    )
    parser.add_argument(
        '--api-port', 
        type=int, 
        default=8000,
        help='API 服务监听端口'
    )
    parser.add_argument(
        '--api-reload', 
        action='store_true',
        help='为 API 服务启用热重载（开发模式）'
    )
    
    # Celery Worker 参数
    parser.add_argument(
        '--worker-concurrency', 
        type=int, 
        default=4,
        help='Celery Worker 并发数量'
    )
    parser.add_argument(
        '--worker-loglevel', 
        type=str, 
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Celery Worker 日志级别'
    )
    parser.add_argument(
        '--worker-queues', 
        type=str, 
        default='default',
        help='Celery Worker 处理的队列，用逗号分隔多个队列'
    )
    parser.add_argument(
        '--worker-events',
        action='store_true',
        help='为 Celery Worker 启用事件通知'
    )
    
    # 通用参数
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='启用全局调试模式 (会覆盖 API 和 Worker 的日志级别)'
    )
    
    # 运行模式
    parser.add_argument(
        '--run-api',
        action='store_true',
        default=True,
        help='启动 API 服务 (默认为 True)'
    )
    parser.add_argument(
        '--run-worker',
        action='store_true',
        default=True,
        help='启动 Celery Worker (默认为 True)'
    )
    parser.add_argument(
        '--no-api',
        action='store_false',
        dest='run_api',
        help='不启动 API 服务'
    )
    parser.add_argument(
        '--no-worker',
        action='store_false',
        dest='run_worker',
        help='不启动 Celery Worker'
    )

    return parser.parse_args()

def run_api_server(args):
    """启动API服务器"""
    cmd = [sys.executable, "run_task_api.py"]
    
    if args.api_host != "0.0.0.0":
        cmd.extend(["--host", args.api_host])
    
    if args.api_port != 8000:
        cmd.extend(["--port", str(args.api_port)])
    
    if args.api_reload:
        cmd.append("--reload")
    
    if args.debug:
        cmd.append("--debug")
    
    logger.info(f"启动 API 服务: {' '.join(cmd)}")
    
    # 在Windows上，不使用shell=True可能会有问题
    use_shell = platform.system() == "Windows"
    return subprocess.Popen(cmd, shell=use_shell)

def run_celery_worker(args):
    """启动Celery Worker"""
    cmd = [sys.executable, "run_celery_worker.py"]
    
    if args.worker_concurrency != 4:
        cmd.extend(["--concurrency", str(args.worker_concurrency)])
    
    if args.worker_loglevel != "info" or args.debug:
        loglevel = "debug" if args.debug else args.worker_loglevel
        cmd.extend(["--loglevel", loglevel])
    
    if args.worker_queues != "default":
        cmd.extend(["--queues", args.worker_queues])
    
    if args.worker_events:
        cmd.append("--events")
    
    logger.info(f"启动 Celery Worker: {' '.join(cmd)}")
    
    # 在Windows上，不使用shell=True可能会有问题
    use_shell = platform.system() == "Windows"
    return subprocess.Popen(cmd, shell=use_shell)

def main():
    """主入口函数"""
    args = parse_args()
    
    processes = []
    
    # 设置全局日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)
        logger.info("全局调试模式已启用")
    
    try:
        # 启动API服务
        if args.run_api:
            api_process = run_api_server(args)
            processes.append(('API服务', api_process))
        
        # 启动Celery Worker
        if args.run_worker:
            worker_process = run_celery_worker(args)
            processes.append(('Celery Worker', worker_process))
        
        if not processes:
            logger.info("没有选择任何服务启动 (API 或 Worker)。请使用 --run-api 或 --run-worker 启动服务。")
            return
        
        # 等待任何子进程退出
        logger.info("所有服务已启动，按 Ctrl+C 终止...")
        
        # 定义一个信号处理函数
        def signal_handler(sig, frame):
            logger.info("收到中断信号，正在关闭服务...")
            for name, proc in processes:
                if proc.poll() is None:  # 如果进程还在运行
                    logger.info(f"正在终止 {name} 进程...")
                    proc.terminate()
            sys.exit(0)
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 等待进程终止
        for name, proc in processes:
            proc.wait()
            logger.info(f"{name} 进程已终止，退出码: {proc.returncode}")
    
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务...")
    finally:
        # 确保所有子进程都被终止
        for name, proc in processes:
            if proc.poll() is None:  # 如果进程还在运行
                logger.info(f"正在终止 {name} 进程...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} 进程未能在5秒内终止，强制终止...")
                    proc.kill()
        logger.info("所有服务已关闭。")

if __name__ == "__main__":
    main() 