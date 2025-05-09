"""
Redis客户端实现
提供与Redis服务器的交互功能和数据缓存能力
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import redis
from redis.exceptions import RedisError as _RedisError

from config import APIConfig

logger = logging.getLogger(__name__)

class RedisError(Exception):
    """Redis操作异常类"""
    pass

class RedisClient:
    """Redis客户端类，提供与Redis服务器的交互功能"""
    
    def __init__(self, config: Optional[APIConfig] = None, url: Optional[str] = None,
                 decode_responses: bool = True, max_connections: int = 10,
                 socket_timeout: int = 10, socket_connect_timeout: int = 10):
        """
        初始化Redis客户端
        
        参数:
        - config: API配置对象，包含Redis连接信息
        - url: Redis连接URL，如果提供则优先使用
        - decode_responses: 是否自动解码响应
        - max_connections: 连接池最大连接数
        - socket_timeout: 套接字超时时间（秒）
        - socket_connect_timeout: 连接超时时间（秒）
        """
        try:
            # 确定连接URL
            if url:
                self.url = url
            elif config and config.redis_url:
                self.url = config.redis_url
            elif config:
                # 构建连接URL
                password_part = f":{config.redis_password}@" if config.redis_password else ""
                protocol = "rediss" if config.redis_ssl else "redis"
                self.url = f"{protocol}://{password_part}{config.redis_host}:{config.redis_port}/{config.redis_db}"
            else:
                # 默认本地Redis
                self.url = "redis://localhost:6379/0"
            
            # 创建连接池
            self.connection_pool = redis.ConnectionPool.from_url(
                self.url,
                decode_responses=decode_responses,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout
            )
            
            # 创建Redis客户端
            self.redis = redis.Redis(connection_pool=self.connection_pool)
            
            # 测试连接
            self.redis.ping()
            logger.info(f"Redis客户端初始化成功: {self.get_sanitized_url()}")
        
        except _RedisError as e:
            logger.error(f"Redis连接失败: {str(e)}")
            raise RedisError(f"无法连接到Redis服务器: {str(e)}")
        except Exception as e:
            logger.error(f"初始化Redis客户端失败: {str(e)}")
            raise RedisError(f"初始化Redis客户端失败: {str(e)}")
    
    def get_sanitized_url(self) -> str:
        """
        获取去除敏感信息的连接URL
        
        返回:
        - str: 去除密码的URL
        """
        # 简单的密码隐藏处理
        url = self.url
        if '@' in url:
            parts = url.split('@')
            proto_auth = parts[0]
            if ':' in proto_auth:
                proto_parts = proto_auth.split(':')
                # 替换密码部分
                if len(proto_parts) >= 3:  # redis://user:password@host
                    url = f"{proto_parts[0]}:{proto_parts[1]}:***@{parts[1]}"
                else:  # redis://:password@host
                    url = f"{proto_parts[0]}:***@{parts[1]}"
        return url
    
    def close(self) -> None:
        """关闭Redis连接池"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.disconnect()
            logger.debug("Redis连接池已关闭")
    
    def __del__(self) -> None:
        """析构函数，确保连接池被关闭"""
        self.close()
    
    def ping(self) -> bool:
        """
        测试与Redis服务器的连接
        
        返回:
        - bool: 连接成功返回True，否则引发异常
        """
        try:
            return self.redis.ping()
        except _RedisError as e:
            logger.error(f"Redis连接测试失败: {str(e)}")
            raise RedisError(f"Redis连接测试失败: {str(e)}")
    
    def set(self, key: str, value: Any, ex: Optional[int] = None, 
            px: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """
        设置键值对
        
        参数:
        - key: 键名
        - value: 值（将自动序列化复杂对象）
        - ex: 过期时间（秒）
        - px: 过期时间（毫秒）
        - nx: 如果设置为True，则只有键不存在时才设置
        - xx: 如果设置为True，则只有键已经存在时才设置
        
        返回:
        - bool: 设置成功返回True，否则返回False
        """
        try:
            # 自动序列化复杂对象
            if not isinstance(value, (str, int, float, bool, bytes)) and value is not None:
                value = json.dumps(value, ensure_ascii=False)
            
            return self.redis.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        except _RedisError as e:
            logger.error(f"Redis设置键值失败: {str(e)}, key={key}")
            raise RedisError(f"Redis设置键值失败: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键值
        
        参数:
        - key: 键名
        - default: 默认值，如果键不存在则返回此值
        
        返回:
        - Any: 键对应的值，如果键不存在则返回默认值
        """
        try:
            value = self.redis.get(key)
            if value is None:
                return default
            
            # 尝试解析JSON
            try:
                # 如果是JSON字符串则解析为对象
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    return json.loads(value)
                return value
            except json.JSONDecodeError:
                # 如果不是有效的JSON，则返回原始值
                return value
            
        except _RedisError as e:
            logger.error(f"Redis获取键值失败: {str(e)}, key={key}")
            raise RedisError(f"Redis获取键值失败: {str(e)}")
    
    def delete(self, *keys: str) -> int:
        """
        删除一个或多个键
        
        参数:
        - keys: 要删除的键名列表
        
        返回:
        - int: 成功删除的键数量
        """
        try:
            return self.redis.delete(*keys)
        except _RedisError as e:
            logger.error(f"Redis删除键失败: {str(e)}, keys={keys}")
            raise RedisError(f"Redis删除键失败: {str(e)}")
    
    def exists(self, *keys: str) -> int:
        """
        检查一个或多个键是否存在
        
        参数:
        - keys: 要检查的键名列表
        
        返回:
        - int: 存在的键数量
        """
        try:
            return self.redis.exists(*keys)
        except _RedisError as e:
            logger.error(f"Redis检查键存在性失败: {str(e)}, keys={keys}")
            raise RedisError(f"Redis检查键存在性失败: {str(e)}")
    
    def expire(self, key: str, time_seconds: int) -> bool:
        """
        设置键的过期时间
        
        参数:
        - key: 键名
        - time_seconds: 过期时间（秒）
        
        返回:
        - bool: 设置成功返回True，否则返回False
        """
        try:
            return self.redis.expire(key, time_seconds)
        except _RedisError as e:
            logger.error(f"Redis设置过期时间失败: {str(e)}, key={key}")
            raise RedisError(f"Redis设置过期时间失败: {str(e)}")
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        参数:
        - key: 键名
        
        返回:
        - int: 剩余秒数，-1表示永不过期，-2表示键不存在
        """
        try:
            return self.redis.ttl(key)
        except _RedisError as e:
            logger.error(f"Redis获取剩余生存时间失败: {str(e)}, key={key}")
            raise RedisError(f"Redis获取剩余生存时间失败: {str(e)}")
    
    def incr(self, key: str, amount: int = 1) -> int:
        """
        将键的整数值增加指定的量
        
        参数:
        - key: 键名
        - amount: 增加的量，默认为1
        
        返回:
        - int: 增加后的值
        """
        try:
            return self.redis.incr(key, amount)
        except _RedisError as e:
            logger.error(f"Redis增加键值失败: {str(e)}, key={key}")
            raise RedisError(f"Redis增加键值失败: {str(e)}")
    
    def decr(self, key: str, amount: int = 1) -> int:
        """
        将键的整数值减少指定的量
        
        参数:
        - key: 键名
        - amount: 减少的量，默认为1
        
        返回:
        - int: 减少后的值
        """
        try:
            return self.redis.decr(key, amount)
        except _RedisError as e:
            logger.error(f"Redis减少键值失败: {str(e)}, key={key}")
            raise RedisError(f"Redis减少键值失败: {str(e)}")
    
    def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置哈希表字段的值
        
        参数:
        - name: 哈希表名
        - key: 字段名
        - value: 字段值（将自动序列化复杂对象）
        
        返回:
        - int: 如果字段是新的并且设置了值，则返回1，如果字段已存在并且更新了值，则返回0
        """
        try:
            # 自动序列化复杂对象
            if not isinstance(value, (str, int, float, bool, bytes)) and value is not None:
                value = json.dumps(value, ensure_ascii=False)
                
            return self.redis.hset(name, key, value)
        except _RedisError as e:
            logger.error(f"Redis设置哈希表字段失败: {str(e)}, name={name}, key={key}")
            raise RedisError(f"Redis设置哈希表字段失败: {str(e)}")
    
    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        获取哈希表字段的值
        
        参数:
        - name: 哈希表名
        - key: 字段名
        - default: 默认值，如果字段不存在则返回此值
        
        返回:
        - Any: 字段的值，如果字段不存在则返回默认值
        """
        try:
            value = self.redis.hget(name, key)
            if value is None:
                return default
            
            # 尝试解析JSON
            try:
                # 如果是JSON字符串则解析为对象
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    return json.loads(value)
                return value
            except json.JSONDecodeError:
                # 如果不是有效的JSON，则返回原始值
                return value
                
        except _RedisError as e:
            logger.error(f"Redis获取哈希表字段失败: {str(e)}, name={name}, key={key}")
            raise RedisError(f"Redis获取哈希表字段失败: {str(e)}")
    
    def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希表的一个或多个字段
        
        参数:
        - name: 哈希表名
        - keys: 要删除的字段名列表
        
        返回:
        - int: 成功删除的字段数量
        """
        try:
            return self.redis.hdel(name, *keys)
        except _RedisError as e:
            logger.error(f"Redis删除哈希表字段失败: {str(e)}, name={name}, keys={keys}")
            raise RedisError(f"Redis删除哈希表字段失败: {str(e)}")
    
    def hexists(self, name: str, key: str) -> bool:
        """
        查看哈希表的指定字段是否存在
        
        参数:
        - name: 哈希表名
        - key: 字段名
        
        返回:
        - bool: 存在返回True，否则返回False
        """
        try:
            return self.redis.hexists(name, key)
        except _RedisError as e:
            logger.error(f"Redis检查哈希表字段存在性失败: {str(e)}, name={name}, key={key}")
            raise RedisError(f"Redis检查哈希表字段存在性失败: {str(e)}")
    
    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取哈希表中的所有字段和值
        
        参数:
        - name: 哈希表名
        
        返回:
        - Dict[str, Any]: 包含所有字段和值的字典
        """
        try:
            result = self.redis.hgetall(name)
            # 尝试解析每个值中的JSON
            for key, value in result.items():
                try:
                    # 如果是JSON字符串则解析为对象
                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                        result[key] = json.loads(value)
                except json.JSONDecodeError:
                    # 如果不是有效的JSON，则保持原始值
                    pass
            return result
        except _RedisError as e:
            logger.error(f"Redis获取全部哈希表字段失败: {str(e)}, name={name}")
            raise RedisError(f"Redis获取全部哈希表字段失败: {str(e)}")
    
    def clean_prefix(self, prefix: str) -> int:
        """
        删除所有指定前缀的键
        
        参数:
        - prefix: 键前缀
        
        返回:
        - int: 删除的键数量
        """
        try:
            pattern = f"{prefix}*"
            keys = self.redis.keys(pattern)
            if not keys:
                return 0
            return self.redis.delete(*keys)
        except _RedisError as e:
            logger.error(f"Redis删除前缀键失败: {str(e)}, prefix={prefix}")
            raise RedisError(f"Redis删除前缀键失败: {str(e)}")
    
    def cache_get(self, key: str, default: Any = None) -> Any:
        """
        从缓存获取值，带自动反序列化功能
        
        参数:
        - key: 缓存键名
        - default: 默认值，如果键不存在则返回此值
        
        返回:
        - Any: 缓存的值，如果键不存在则返回默认值
        """
        return self.get(key, default)
    
    def cache_set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        设置缓存值，带自动序列化和过期时间
        
        参数:
        - key: 缓存键名
        - value: 要缓存的值
        - timeout: 过期时间（秒），如果为None则永不过期
        
        返回:
        - bool: 设置成功返回True，否则返回False
        """
        return self.set(key, value, ex=timeout)
    
    def cache_delete(self, key: str) -> int:
        """
        删除缓存项
        
        参数:
        - key: 缓存键名
        
        返回:
        - int: 删除的键数量
        """
        return self.delete(key)
    
    def cache_clear(self, prefix: str = "") -> int:
        """
        清除缓存（全部或指定前缀）
        
        参数:
        - prefix: 缓存键前缀，如果为空则清除所有缓存
        
        返回:
        - int: 删除的键数量
        """
        try:
            if not prefix:
                # 警告: 这将删除整个数据库中的所有键
                return self.redis.flushdb()
            else:
                return self.clean_prefix(prefix)
        except _RedisError as e:
            logger.error(f"Redis清除缓存失败: {str(e)}, prefix={prefix}")
            raise RedisError(f"Redis清除缓存失败: {str(e)}") 