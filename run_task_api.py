"""
任务队列API启动脚本
提供便捷的命令行方式启动API服务
"""

import argparse
import os
import logging
from uvicorn import run

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动任务队列API服务')
    parser.add_argument(
        '--host', 
        type=str, 
        default='0.0.0.0',
        help='服务监听地址'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=8000,
        help='服务监听端口'
    )
    parser.add_argument(
        '--reload', 
        action='store_true',
        help='启用热重载（开发模式）'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='启用调试模式'
    )
    return parser.parse_args()

def main():
    """主入口函数"""
    args = parse_args()
    
    # 设置环境变量
    if args.debug:
        os.environ['LOG_LEVEL'] = 'DEBUG'
        log_level = 'debug'
    else:
        os.environ['LOG_LEVEL'] = 'INFO'
        log_level = 'info'
    
    # 打印启动信息
    logger.info(f"启动任务队列API服务，地址: {args.host}:{args.port}")
    
    # 启动uvicorn服务器
    run(
        "task_api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=log_level
    )

if __name__ == "__main__":
    main() 