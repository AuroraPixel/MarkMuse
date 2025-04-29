"""
存储服务抽象接口
定义所有存储服务必须实现的方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Union, Any


class StorageError(Exception):
    """存储服务错误基类"""
    pass


class Storage(ABC):
    """
    存储服务抽象接口
    所有具体的存储实现都应该继承自此类
    """
    
    @abstractmethod
    def upload_file(self, local_file_path: str, remote_path: str = None, content_type: str = None) -> Optional[str]:
        """
        上传文件到存储服务
        
        参数:
        - local_file_path: 本地文件路径
        - remote_path: 远程存储路径，如果为 None，则使用文件名
        - content_type: 文件内容类型
        
        返回:
        - 文件的公共访问 URL，如果上传失败返回 None
        
        抛出:
        - StorageError: 上传失败
        """
        pass
    
    @abstractmethod
    def upload_directory(self, local_dir: str, remote_prefix: str = "") -> Dict[str, str]:
        """
        上传整个目录到存储服务
        
        参数:
        - local_dir: 本地目录路径
        - remote_prefix: 远程存储路径前缀
        
        返回:
        - 字典，键为本地文件路径，值为远程访问 URL
        
        抛出:
        - StorageError: 上传失败
        """
        pass
    
    @abstractmethod
    def get_public_url(self, remote_path: str) -> str:
        """
        获取远程文件的公共访问 URL
        
        参数:
        - remote_path: 远程存储路径
        
        返回:
        - 公共访问 URL
        """
        pass 