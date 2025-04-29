"""
存储模块，提供各种存储服务的统一接口
"""

from .abstract_storage import Storage, StorageError
from .s3_storage import S3Storage

__all__ = ['Storage', 'StorageError', 'S3Storage'] 