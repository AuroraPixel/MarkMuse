#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库模块测试: 用于测试数据库连接、表创建和CRUD操作
"""

import os
import sys
import logging
import unittest
import tempfile
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

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

# 尝试导入数据库模块
try:
    from clients.db.models import ExampleTable, Base
    from clients.db.database import init_db
    from clients.db.crud import create_example_item
except ImportError:
    logger.error("未能导入数据库模块，请确保项目结构正确")
    sys.exit(1)

# 尝试导入配置模块
try:
    from config.api_config import get_db
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    logger.warning("未找到配置模块，将使用测试数据库配置")

# 加载环境变量
load_dotenv()


class DBTest(unittest.TestCase):
    """测试数据库功能"""
    
    def setUp(self):
        """测试前准备工作"""
        # 检查是否使用本地SQLite测试数据库还是配置的数据库
        self.use_sqlite = not os.getenv('DATABASE_URL')
        
        if self.use_sqlite:
            # 创建临时SQLite数据库用于测试
            self.db_fd, self.db_path = tempfile.mkstemp()
            self.db_url = f"sqlite:///{self.db_path}"
            logger.info(f"使用临时SQLite数据库: {self.db_url}")
        else:
            # 使用环境变量中的数据库URL
            self.db_url = os.getenv('DATABASE_URL')
            if not self.db_url:
                self.skipTest("跳过测试，未设置DATABASE_URL环境变量")
            
            # 为测试添加前缀，避免与生产数据库冲突
            if 'postgresql' in self.db_url:
                # 如果是PostgreSQL，可以添加schema前缀
                logger.info("使用PostgreSQL数据库进行测试")
            
        # 初始化测试数据库
        try:
            self.engine = create_engine(self.db_url, echo=True)
            self.Session = sessionmaker(bind=self.engine)
            
            # 创建所有表
            Base.metadata.create_all(self.engine)
            logger.info("成功创建测试数据库表")
        except Exception as e:
            logger.error(f"初始化测试数据库失败: {str(e)}")
            self.fail(f"数据库初始化失败: {str(e)}")
    
    def tearDown(self):
        """测试后清理工作"""
        # 关闭数据库连接
        if hasattr(self, 'engine'):
            self.engine.dispose()
        
        # 如果使用SQLite，删除临时文件
        if hasattr(self, 'use_sqlite') and self.use_sqlite:
            if hasattr(self, 'db_fd'):
                os.close(self.db_fd)
            if hasattr(self, 'db_path') and os.path.exists(self.db_path):
                os.unlink(self.db_path)
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            # 创建会话并尝试查询
            session = self.Session()
            
            # 执行简单查询，检查连接是否正常
            result = session.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1, "数据库查询应返回1")
            
            # 检查数据库表是否存在
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            # 检查ExampleTable表是否存在
            self.assertIn('example_table', tables, "example_table表应该存在")
            
            logger.info("数据库连接测试通过")
            session.close()
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            self.fail(f"数据库连接测试失败: {str(e)}")
    
    def test_create_table(self):
        """测试表结构创建"""
        try:
            from sqlalchemy import inspect
            
            # 创建会话
            session = self.Session()
            
            # 获取表结构信息
            inspector = inspect(self.engine)
            columns = inspector.get_columns('example_table')
            
            # 检查列信息
            column_names = [col['name'] for col in columns]
            expected_columns = ['id', 'name', 'description', 'created_at', 'updated_at', 'active']
            
            # 验证所有预期的列都存在
            for column in expected_columns:
                self.assertIn(column, column_names, f"表中应存在列: {column}")
            
            # 检查主键
            pk = inspector.get_pk_constraint('example_table')
            pk_columns = pk.get('constrained_columns', [])
            self.assertEqual(pk_columns, ['id'], "主键应为id列")
            
            # 检查索引
            indexes = inspector.get_indexes('example_table')
            index_names = [idx['name'] for idx in indexes]
            self.assertTrue(any('name' in idx_name.lower() for idx_name in index_names), 
                          "应存在name列的索引")
            
            logger.info("表结构测试通过")
            session.close()
        except Exception as e:
            logger.error(f"表结构测试失败: {str(e)}")
            self.fail(f"表结构测试失败: {str(e)}")
    
    def test_crud_operations(self):
        """测试CRUD操作"""
        try:
            # 创建会话
            session = self.Session()
            
            # 1. 创建操作 (CREATE)
            test_data = {
                'name': '测试项目',
                'description': '这是一个测试描述',
                'active': True
            }
            
            # 使用CRUD模块创建项目
            created_item = create_example_item(session, test_data)
            self.assertIsNotNone(created_item, "创建的项目不应为None")
            self.assertIsNotNone(created_item.id, "创建的项目应有ID")
            self.assertEqual(created_item.name, test_data['name'], "名称应与输入一致")
            
            # 2. 读取操作 (READ)
            # 通过ID查询
            queried_item = session.query(ExampleTable).filter(ExampleTable.id == created_item.id).first()
            self.assertIsNotNone(queried_item, "应能通过ID查询到项目")
            self.assertEqual(queried_item.name, test_data['name'], "查询结果的名称应与创建时一致")
            
            # 通过名称查询
            queried_items = session.query(ExampleTable).filter(ExampleTable.name == test_data['name']).all()
            self.assertGreater(len(queried_items), 0, "应能通过名称查询到项目")
            
            # 3. 更新操作 (UPDATE)
            queried_item.name = "已更新的名称"
            session.commit()
            
            # 重新查询验证更新
            updated_item = session.query(ExampleTable).filter(ExampleTable.id == created_item.id).first()
            self.assertEqual(updated_item.name, "已更新的名称", "名称应已更新")
            
            # 4. 删除操作 (DELETE)
            session.delete(updated_item)
            session.commit()
            
            # 验证删除
            deleted_check = session.query(ExampleTable).filter(ExampleTable.id == created_item.id).first()
            self.assertIsNone(deleted_check, "删除后查询应返回None")
            
            # 批量操作测试
            # 批量插入多条数据
            for i in range(5):
                item_data = {
                    'name': f'批量测试项目-{i}',
                    'description': f'批量测试描述-{i}',
                    'active': True
                }
                create_example_item(session, item_data)
            
            # 验证批量插入
            batch_items = session.query(ExampleTable).filter(
                ExampleTable.name.like('批量测试项目-%')
            ).all()
            self.assertEqual(len(batch_items), 5, "应能批量插入5条数据")
            
            # 测试过滤条件
            active_items = session.query(ExampleTable).filter(
                ExampleTable.active == True
            ).all()
            self.assertGreaterEqual(len(active_items), 5, "应至少有5条激活状态的数据")
            
            logger.info("CRUD操作测试通过")
            session.close()
        except Exception as e:
            logger.error(f"CRUD操作测试失败: {str(e)}")
            self.fail(f"CRUD操作测试失败: {str(e)}")


def setup_test_db():
    """设置测试数据库环境"""
    # 如果没有设置DATABASE_URL，使用临时SQLite数据库
    if not os.getenv('DATABASE_URL'):
        # 使用内存数据库
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        logger.info("未设置DATABASE_URL，使用SQLite内存数据库")
    else:
        logger.info(f"使用环境变量中的数据库: {os.getenv('DATABASE_URL')}")


def run_db_tests():
    """运行数据库测试"""
    # 设置测试数据库环境
    setup_test_db()
    
    # 运行测试用例
    suite = unittest.TestLoader().loadTestsFromTestCase(DBTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    """主函数：直接运行测试"""
    logger.info("开始数据库功能测试...")
    
    # 运行所有数据库测试
    run_db_tests()
    
    logger.info("数据库功能测试完成")


if __name__ == '__main__':
    main() 