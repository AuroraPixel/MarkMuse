#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis模块测试: 用于测试Redis连接和操作
"""

import os
import sys
import logging
import unittest
import json
import time
from dotenv import load_dotenv

# 确保可以导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入Redis模块
try:
    from clients.redis import RedisClient, RedisError
    from clients.factory import create_redis_client
except ImportError:
    logger.error("未能导入Redis模块，请确保项目结构正确")
    sys.exit(1)

# 尝试导入配置模块
try:
    from config import load_api_config
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    logger.warning("未找到配置模块，将使用默认Redis配置")

# 加载环境变量
load_dotenv()


class RedisTest(unittest.TestCase):
    """测试Redis功能"""
    
    def setUp(self):
        """测试前准备工作"""
        # 检查是否配置了Redis
        self.redis_url = os.getenv('REDIS_URL')
        
        try:
            if USE_CONFIG:
                # 使用配置创建Redis客户端
                config = load_api_config()
                self.redis = create_redis_client(config)
                logger.info("使用配置创建Redis客户端")
            else:
                # 直接创建Redis客户端
                self.redis = RedisClient(url=self.redis_url)
                logger.info("直接创建Redis客户端")
                
            # 测试连接
            self.redis.ping()
            
            # 设置测试前缀，避免影响生产数据
            self.test_prefix = "test:redis:"
            
        except RedisError as e:
            logger.error(f"Redis连接失败: {str(e)}")
            self.fail(f"Redis连接失败: {str(e)}")
    
    def tearDown(self):
        """测试后清理工作"""
        if hasattr(self, 'redis') and self.redis:
            # 清理测试数据
            try:
                keys = self.redis.redis.keys(f"{self.test_prefix}*")
                if keys:
                    self.redis.redis.delete(*keys)
                    logger.info(f"已清理 {len(keys)} 个测试键")
            except Exception as e:
                logger.warning(f"清理测试数据失败: {str(e)}")
            
            # 关闭连接
            self.redis.close()
            logger.info("Redis连接已关闭")
    
    def test_connection(self):
        """测试Redis连接"""
        try:
            # 测试ping操作
            result = self.redis.ping()
            self.assertTrue(result, "Redis ping应返回True")
            logger.info("Redis连接测试通过")
        except Exception as e:
            logger.error(f"Redis连接测试失败: {str(e)}")
            self.fail(f"Redis连接测试失败: {str(e)}")
    
    def test_basic_operations(self):
        """测试基本操作（set/get/delete）"""
        try:
            # 测试键值
            test_key = f"{self.test_prefix}basic"
            test_value = "测试值"
            
            # 测试set操作
            set_result = self.redis.set(test_key, test_value)
            self.assertTrue(set_result, "set操作应返回True")
            
            # 测试get操作
            get_result = self.redis.get(test_key)
            self.assertEqual(get_result, test_value, "get操作应返回设置的值")
            
            # 测试exists操作
            exists_result = self.redis.exists(test_key)
            self.assertEqual(exists_result, 1, "exists操作应返回1")
            
            # 测试过期时间
            expire_time = 2
            expire_result = self.redis.expire(test_key, expire_time)
            self.assertTrue(expire_result, "expire操作应返回True")
            
            # 测试ttl操作
            ttl_result = self.redis.ttl(test_key)
            self.assertGreaterEqual(ttl_result, 1, "ttl操作应返回大于等于1的值")
            
            # 等待键过期
            time.sleep(expire_time + 1)
            
            # 测试过期后的get操作
            expired_result = self.redis.get(test_key)
            self.assertIsNone(expired_result, "过期后get操作应返回None")
            
            # 重新设置键值
            self.redis.set(test_key, test_value)
            
            # 测试delete操作
            delete_result = self.redis.delete(test_key)
            self.assertEqual(delete_result, 1, "delete操作应返回1")
            
            # 测试delete后的get操作
            after_delete = self.redis.get(test_key)
            self.assertIsNone(after_delete, "delete后get操作应返回None")
            
            logger.info("Redis基本操作测试通过")
        except Exception as e:
            logger.error(f"Redis基本操作测试失败: {str(e)}")
            self.fail(f"Redis基本操作测试失败: {str(e)}")
    
    def test_numeric_operations(self):
        """测试数值操作（incr/decr）"""
        try:
            # 测试键
            test_key = f"{self.test_prefix}numeric"
            
            # 测试incr操作
            incr_result = self.redis.incr(test_key)
            self.assertEqual(incr_result, 1, "incr操作应返回1")
            
            # 再次测试incr操作
            incr_result = self.redis.incr(test_key)
            self.assertEqual(incr_result, 2, "再次incr操作应返回2")
            
            # 测试带数量的incr操作
            incr_amount_result = self.redis.incr(test_key, 3)
            self.assertEqual(incr_amount_result, 5, "带数量的incr操作应返回5")
            
            # 测试decr操作
            decr_result = self.redis.decr(test_key)
            self.assertEqual(decr_result, 4, "decr操作应返回4")
            
            # 测试带数量的decr操作
            decr_amount_result = self.redis.decr(test_key, 2)
            self.assertEqual(decr_amount_result, 2, "带数量的decr操作应返回2")
            
            logger.info("Redis数值操作测试通过")
        except Exception as e:
            logger.error(f"Redis数值操作测试失败: {str(e)}")
            self.fail(f"Redis数值操作测试失败: {str(e)}")
    
    def test_hash_operations(self):
        """测试哈希表操作（hset/hget/hdel/hgetall）"""
        try:
            # 测试哈希表名
            test_hash = f"{self.test_prefix}hash"
            
            # 测试hset操作
            hset_result = self.redis.hset(test_hash, "field1", "value1")
            self.assertEqual(hset_result, 1, "hset新字段应返回1")
            
            # 测试hget操作
            hget_result = self.redis.hget(test_hash, "field1")
            self.assertEqual(hget_result, "value1", "hget操作应返回设置的值")
            
            # 测试hexists操作
            hexists_result = self.redis.hexists(test_hash, "field1")
            self.assertTrue(hexists_result, "hexists操作应返回True")
            
            # 测试不存在的字段
            hget_nonexist = self.redis.hget(test_hash, "nonexistent", "default")
            self.assertEqual(hget_nonexist, "default", "hget不存在的字段应返回默认值")
            
            # 添加多个字段
            self.redis.hset(test_hash, "field2", "value2")
            self.redis.hset(test_hash, "field3", "value3")
            
            # 测试hgetall操作
            hgetall_result = self.redis.hgetall(test_hash)
            self.assertIsInstance(hgetall_result, dict, "hgetall操作应返回字典")
            self.assertEqual(len(hgetall_result), 3, "hgetall操作应返回3个字段")
            self.assertEqual(hgetall_result["field1"], "value1", "字段1的值应为value1")
            self.assertEqual(hgetall_result["field2"], "value2", "字段2的值应为value2")
            self.assertEqual(hgetall_result["field3"], "value3", "字段3的值应为value3")
            
            # 测试hdel操作
            hdel_result = self.redis.hdel(test_hash, "field1", "field2")
            self.assertEqual(hdel_result, 2, "hdel操作应返回2")
            
            # 测试hdel后的hgetall
            after_hdel = self.redis.hgetall(test_hash)
            self.assertEqual(len(after_hdel), 1, "hdel后应只剩1个字段")
            self.assertEqual(after_hdel["field3"], "value3", "剩余字段的值应为value3")
            
            logger.info("Redis哈希表操作测试通过")
        except Exception as e:
            logger.error(f"Redis哈希表操作测试失败: {str(e)}")
            self.fail(f"Redis哈希表操作测试失败: {str(e)}")
    
    def test_serialization(self):
        """测试JSON序列化和反序列化"""
        try:
            # 测试键
            test_key = f"{self.test_prefix}json"
            test_hash = f"{self.test_prefix}json_hash"
            
            # 测试复杂对象
            test_object = {
                "name": "测试对象",
                "attributes": {
                    "int_value": 42,
                    "float_value": 3.14,
                    "bool_value": True,
                    "null_value": None
                },
                "list_value": [1, 2, 3, 4, 5],
                "nested": {
                    "child1": {"value": "嵌套1"},
                    "child2": {"value": "嵌套2"}
                }
            }
            
            # 测试set操作（自动序列化）
            set_result = self.redis.set(test_key, test_object)
            self.assertTrue(set_result, "set复杂对象应返回True")
            
            # 测试get操作（自动反序列化）
            get_result = self.redis.get(test_key)
            self.assertEqual(get_result, test_object, "get操作应返回原始对象")
            self.assertEqual(get_result["name"], test_object["name"], "对象name应一致")
            self.assertEqual(get_result["attributes"]["int_value"], 42, "int值应为42")
            self.assertEqual(len(get_result["list_value"]), 5, "列表长度应为5")
            
            # 测试hash中的序列化和反序列化
            hset_result = self.redis.hset(test_hash, "object", test_object)
            self.assertEqual(hset_result, 1, "hset复杂对象应返回1")
            
            # 测试hget操作（自动反序列化）
            hget_result = self.redis.hget(test_hash, "object")
            self.assertEqual(hget_result, test_object, "hget操作应返回原始对象")
            
            logger.info("Redis序列化测试通过")
        except Exception as e:
            logger.error(f"Redis序列化测试失败: {str(e)}")
            self.fail(f"Redis序列化测试失败: {str(e)}")
    
    def test_cache_methods(self):
        """测试缓存API（cache_set/cache_get/cache_delete/cache_clear）"""
        try:
            # 测试键前缀
            cache_prefix = f"{self.test_prefix}cache:"
            
            # 测试cache_set操作
            cache_set_result = self.redis.cache_set(f"{cache_prefix}key1", "value1", 60)
            self.assertTrue(cache_set_result, "cache_set操作应返回True")
            
            # 测试cache_get操作
            cache_get_result = self.redis.cache_get(f"{cache_prefix}key1")
            self.assertEqual(cache_get_result, "value1", "cache_get操作应返回设置的值")
            
            # 测试不存在的键
            cache_get_nonexist = self.redis.cache_get(f"{cache_prefix}nonexistent", "default")
            self.assertEqual(cache_get_nonexist, "default", "cache_get不存在的键应返回默认值")
            
            # 添加更多缓存项
            self.redis.cache_set(f"{cache_prefix}key2", "value2")
            self.redis.cache_set(f"{cache_prefix}key3", "value3")
            
            # 测试cache_delete操作
            cache_delete_result = self.redis.cache_delete(f"{cache_prefix}key1")
            self.assertEqual(cache_delete_result, 1, "cache_delete操作应返回1")
            
            # 测试cache_clear前缀操作
            # 先确认存在2个以该前缀开头的键
            keys_before_clear = self.redis.redis.keys(f"{cache_prefix}*")
            self.assertEqual(len(keys_before_clear), 2, "清理前应有2个缓存项")
            
            # 清理前缀
            cache_clear_result = self.redis.cache_clear(cache_prefix)
            self.assertEqual(cache_clear_result, 2, "cache_clear操作应返回2")
            
            # 验证已清理
            keys_after_clear = self.redis.redis.keys(f"{cache_prefix}*")
            self.assertEqual(len(keys_after_clear), 0, "清理后应有0个缓存项")
            
            logger.info("Redis缓存API测试通过")
        except Exception as e:
            logger.error(f"Redis缓存API测试失败: {str(e)}")
            self.fail(f"Redis缓存API测试失败: {str(e)}")


def setup_test_redis():
    """设置测试Redis环境"""
    # 如果没有设置REDIS_URL，使用默认配置
    if not os.getenv('REDIS_URL'):
        default_url = "redis://localhost:6379/0"
        os.environ['REDIS_URL'] = default_url
        logger.info(f"未设置REDIS_URL，使用默认URL: {default_url}")
    else:
        logger.info(f"使用环境变量中的Redis: {os.getenv('REDIS_URL')}")


def run_redis_tests():
    """运行Redis测试"""
    # 设置测试Redis环境
    setup_test_redis()
    
    # 运行测试用例
    suite = unittest.TestLoader().loadTestsFromTestCase(RedisTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    """主函数：直接运行测试"""
    logger.info("开始Redis功能测试...")
    
    # 运行所有Redis测试
    run_redis_tests()
    
    logger.info("Redis功能测试完成")


if __name__ == '__main__':
    main() 