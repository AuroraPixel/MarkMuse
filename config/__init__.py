"""
配置模块，提供统一的配置管理
"""

from .api_config import load_api_config, APIConfig

__all__ = ['load_api_config', 'APIConfig'] 