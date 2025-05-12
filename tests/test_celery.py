#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery模块测试: 用于测试Celery任务队列配置和任务执行
"""

import os
import sys
import logging
import unittest
import json
import time
import threading
from datetime import timedelta
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

# 尝试导入Celery模块
try:
    from clients.celery import celery_app, configure_celery, BaseTask, register_task
    from clients.celery.tasks import AsyncTask, PeriodicTask, example_task
    from clients.factory import create_celery_app
except ImportError:
    logger.error("未能导入Celery模块，请确保项目结构正确")
    sys.exit(1)

# 尝试导入Redis模块（用于检查Celery结果存储）
try:
    from clients.redis import RedisClient
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("未能导入Redis模块，部分测试将跳过")

# 尝试导入配置模块
try:
    from config import load_api_config
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    logger.warning("未找到配置模块，将使用默认Celery配置")

# 加载环境变量
load_dotenv()


class CeleryTest(unittest.TestCase):
    """测试Celery功能"""
    
    def setUp(self):
        """测试前准备工作"""
        # 强制启用任务eager执行模式，避免需要运行celery worker
        os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'true'
        os.environ['CELERY_TASK_EAGER_PROPAGATES'] = 'true'
        
        try:
            if USE_CONFIG:
                # 使用配置创建Celery应用
                config = load_api_config()
                self.app = create_celery_app(config)
                logger.info("使用配置创建Celery应用")
            else:
                # 直接配置Celery应用
                self.app = configure_celery(celery_app, broker_url='memory://', result_backend='cache')
                logger.info("直接配置Celery应用（内存模式）")
            
            # 强制设置为eager模式
            self.app.conf.task_always_eager = True
            self.app.conf.task_eager_propagates = True
            
            # 如果有Redis，创建Redis客户端用于验证结果
            self.redis = None
            if HAS_REDIS and os.getenv('REDIS_URL'):
                try:
                    self.redis = RedisClient(url=os.getenv('REDIS_URL'))
                    logger.info("已连接Redis，可验证Celery任务结果")
                except Exception as e:
                    logger.warning(f"连接Redis失败: {str(e)}，跳过结果验证")
            
        except Exception as e:
            logger.error(f"Celery测试环境设置失败: {str(e)}")
            self.fail(f"Celery测试环境设置失败: {str(e)}")
    
    def tearDown(self):
        """测试后清理工作"""
        # 清理Redis资源
        if hasattr(self, 'redis') and self.redis:
            self.redis.close()
            logger.info("Redis连接已关闭")
    
    def test_app_creation(self):
        """测试Celery应用创建和配置"""
        try:
            # 验证应用配置
            self.assertEqual(self.app.conf.task_serializer, 'json', "任务序列化器应为json")
            self.assertTrue(self.app.conf.task_always_eager, "应启用eager模式")
            self.assertTrue(self.app.conf.task_eager_propagates, "应启用eager异常传播")
            
            # 检查broker_url配置
            self.assertIsNotNone(self.app.conf.broker_url, "broker_url不应为None")
            
            # 检查result_backend配置
            self.assertIsNotNone(self.app.conf.result_backend, "result_backend不应为None")
            
            logger.info("Celery应用创建测试通过")
        except Exception as e:
            logger.error(f"Celery应用创建测试失败: {str(e)}")
            self.fail(f"Celery应用创建测试失败: {str(e)}")
    
    def test_basic_task(self):
        """测试基本任务执行"""
        try:
            # 定义简单任务
            @self.app.task
            def add(x, y):
                return x + y
            
            # 执行任务
            result = add.delay(4, 4)
            
            # 等待任务完成
            value = result.get(timeout=5)
            
            # 验证结果
            self.assertEqual(value, 8, "4+4应该等于8")
            
            logger.info("基本任务执行测试通过")
        except Exception as e:
            logger.error(f"基本任务执行测试失败: {str(e)}")
            self.fail(f"基本任务执行测试失败: {str(e)}")
    
    def test_task_registration(self):
        """测试任务注册装饰器"""
        try:
            # 使用app直接注册任务
            @self.app.task(base=BaseTask, name='test.multiply', bind=True)
            def multiply(self, x, y):
                return x * y
            
            # 验证任务名称
            name = multiply.name
            self.assertEqual(name, 'test.multiply', "任务名称应为test.multiply")
            
            # 执行任务
            result = multiply.delay(5, 6)
            
            # 等待任务完成
            value = result.get(timeout=5)
            
            # 验证结果
            self.assertEqual(value, 30, "5*6应该等于30")
            
            logger.info("任务注册测试通过")
        except Exception as e:
            logger.error(f"任务注册测试失败: {str(e)}")
            self.fail(f"任务注册测试失败: {str(e)}")
    
    def test_custom_task_class(self):
        """测试自定义任务类"""
        try:
            class CustomAsyncTask(AsyncTask):
                def preprocess(self, x, y):
                    # 在参数上加1
                    return {'x': x + 1, 'y': y + 1}
                
                def execute(self, data):
                    # 执行乘法
                    return data['x'] * data['y']
                
                def postprocess(self, result):
                    # 结果加10
                    return result + 10
            
            # 创建任务实例
            task_cls = self.app.task(
                name='test.custom_process',
                base=CustomAsyncTask,
                bind=True
            )
            
            # 创建任务函数
            @task_cls
            def process_custom(self, x, y):
                # Manually call the pipeline defined in AsyncTask/CustomAsyncTask
                processed_data = self.preprocess(x, y) # Calls CustomAsyncTask.preprocess
                result = self.execute(processed_data)    # Calls CustomAsyncTask.execute
                final_result = self.postprocess(result)  # Calls CustomAsyncTask.postprocess
                return final_result
            
            # 执行任务
            result = process_custom.delay(3, 4)
            
            # 等待任务完成
            value = result.get(timeout=5)
            
            # 验证结果: (3+1)*(4+1) + 10 = 4*5 + 10 = 30
            self.assertEqual(value, 30, "计算结果应为30")
            
            logger.info("自定义任务类测试通过")
        except Exception as e:
            logger.error(f"自定义任务类测试失败: {str(e)}")
            self.fail(f"自定义任务类测试失败: {str(e)}")
    
    def test_example_task(self):
        """测试示例任务"""
        try:
            # 直接使用已定义的example_task
            # 执行示例任务，设置较短的延迟
            task_name = "测试任务"
            delay = 0.1  # 设置较短的延迟以加快测试
            
            # 创建任务实例
            task_obj = example_task
            
            # 确保任务被正确注册
            self.assertIsNotNone(task_obj, "示例任务应被正确注册")
            
            # 执行任务
            result = task_obj.delay(task_name, delay)
            
            # 等待任务完成
            task_result = result.get(timeout=5)
            
            # 验证结果
            self.assertIsInstance(task_result, dict, "结果应为字典")
            self.assertEqual(task_result["task_name"], task_name, f"任务名称应为{task_name}")
            self.assertEqual(task_result["status"], "成功", "任务状态应为成功")
            self.assertIn("details", task_result, "结果应包含details字段")
            self.assertEqual(task_result["details"]["steps_completed"], 5, "应完成5个步骤")
            
            logger.info("示例任务测试通过")
        except Exception as e:
            logger.error(f"示例任务测试失败: {str(e)}")
            self.fail(f"示例任务测试失败: {str(e)}")
    
    def test_periodic_task(self):
        """测试定期任务"""
        try:
            # 创建定期任务类
            class TestPeriodic(PeriodicTask):
                name = "test.periodic_task"
                run_every = timedelta(hours=1)  # 每小时运行一次
                
                def execute(self, data):
                    return {"status": "success", "timestamp": time.time()}
            
            # 注册任务类
            @self.app.task(base=TestPeriodic, bind=True, name='test.periodic_task_run')
            def periodic_run(self):
                # Manually call the pipeline
                processed_data = self.preprocess() # Calls AsyncTask.preprocess (default)
                result = self.execute(processed_data)    # Calls TestPeriodic.execute
                final_result = self.postprocess(result)  # Calls AsyncTask.postprocess (default)
                return final_result
            
            # 执行任务
            result = periodic_run.delay()
            
            # 等待任务完成
            task_result = result.get(timeout=5)
            
            # 验证结果
            self.assertIsInstance(task_result, dict, "结果应为字典")
            self.assertEqual(task_result["status"], "success", "任务状态应为success")
            self.assertIn("timestamp", task_result, "结果应包含timestamp字段")
            
            logger.info("定期任务测试通过")
        except Exception as e:
            logger.error(f"定期任务测试失败: {str(e)}")
            self.fail(f"定期任务测试失败: {str(e)}")
    
    def test_task_progress(self):
        """测试任务进度跟踪"""
        try:
            # 定义带进度跟踪的任务类
            progress_updates = []
            
            class ProgressAsyncTask(AsyncTask):
                def preprocess(self, *args, **kwargs):
                    # 简单返回空数据
                    return {}
                
                def execute(self, data):
                    total_steps = 5
                    for i in range(1, total_steps + 1):
                        # 计算并更新进度
                        progress = i * 20  # 每步20%
                        self.update_progress(progress, f"步骤 {i}/{total_steps}")
                        
                        # 记录进度更新到外部列表
                        nonlocal progress_updates
                        progress_updates.append((progress, f"步骤 {i}/{total_steps}"))
                        
                        # 模拟处理
                        time.sleep(0.1)
                    
                    return {"completed": True, "steps": total_steps}
            
            # 注册任务
            @self.app.task(base=ProgressAsyncTask, bind=True, name='test.progress_run')
            def progress_task(self):
                # Manually call the pipeline
                processed_data = self.preprocess() # Calls ProgressAsyncTask.preprocess
                result = self.execute(processed_data)    # Calls ProgressAsyncTask.execute
                final_result = self.postprocess(result)  # Calls AsyncTask.postprocess (default)
                return final_result
            
            # 执行任务
            result = progress_task.delay()
            
            # 等待任务完成
            task_result = result.get(timeout=5)
            
            # 验证结果
            self.assertTrue(task_result["completed"], "任务应标记为已完成")
            self.assertEqual(task_result["steps"], 5, "应完成5个步骤")
            
            # 验证进度更新
            self.assertEqual(len(progress_updates), 5, "应有5次进度更新")
            
            # 验证最后一次进度
            last_progress, last_message = progress_updates[-1]
            self.assertEqual(last_progress, 100, "最终进度应为100%")
            self.assertEqual(last_message, "步骤 5/5", "最终消息应为'步骤 5/5'")
            
            logger.info("任务进度跟踪测试通过")
        except Exception as e:
            logger.error(f"任务进度跟踪测试失败: {str(e)}")
            self.fail(f"任务进度跟踪测试失败: {str(e)}")
    
    def test_error_handling(self):
        """测试任务错误处理"""
        try:
            # 跟踪重试次数
            # retry_count = [0]
            
            # 定义会失败的任务，使用Celery内置的重试计数
            @self.app.task(bind=True, max_retries=2)
            def failing_task(self):
                # retry_count[0] += 1
                logger.info(f"Failing task attempt: {self.request.retries + 1} of {self.max_retries + 1}")
                if self.request.retries < self.max_retries: # self.max_retries 是从装饰器来的
                    # raise ValueError("任务失败，需要重试") # 原来的方式
                    # 显式要求Celery重试，并传递原始异常
                    raise self.retry(exc=ValueError("任务失败，需要重试"), countdown=1) 
                logger.info("Failing task succeeded on the last attempt.")
                return "成功"
            
            # 临时禁用eager传播以允许重试
            original_propagate = self.app.conf.task_eager_propagates
            self.app.conf.task_eager_propagates = False
            
            try:
                # 执行任务
                result = failing_task.delay()
                
                # 等待任务完成
                task_result = result.get(timeout=5)
                
                # 验证结果（应在第三次尝试成功）
                self.assertEqual(task_result, "成功", "第三次尝试应成功")
                # self.assertEqual(retry_count[0], 3, "应重试2次，总共执行3次") # 移除对外部计数器的断言
                
            finally:
                # 恢复原始设置
                self.app.conf.task_eager_propagates = original_propagate
            
            logger.info("任务错误处理测试通过")
        except Exception as e:
            logger.error(f"任务错误处理测试失败: {str(e)}")
            self.fail(f"任务错误处理测试失败: {str(e)}")


def setup_test_celery():
    """设置测试Celery环境"""
    # 如果没有设置CELERY_BROKER_URL，使用内存模式
    if not os.getenv('CELERY_BROKER_URL'):
        os.environ['CELERY_BROKER_URL'] = 'memory://'
        logger.info("未设置CELERY_BROKER_URL，使用内存模式")
    
    # 如果没有设置CELERY_RESULT_BACKEND，使用缓存模式
    if not os.getenv('CELERY_RESULT_BACKEND'):
        os.environ['CELERY_RESULT_BACKEND'] = 'cache'
        logger.info("未设置CELERY_RESULT_BACKEND，使用缓存模式")
    
    # 启用eager模式
    os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'true'
    os.environ['CELERY_TASK_EAGER_PROPAGATES'] = 'true'
    logger.info("已启用Celery eager模式，无需运行worker")


def run_celery_tests():
    """运行Celery测试"""
    # 设置测试Celery环境
    setup_test_celery()
    
    # 运行测试用例
    suite = unittest.TestLoader().loadTestsFromTestCase(CeleryTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    """主函数：直接运行测试"""
    logger.info("开始Celery功能测试...")
    
    # 运行所有Celery测试
    run_celery_tests()
    
    logger.info("Celery功能测试完成")


if __name__ == '__main__':
    main() 