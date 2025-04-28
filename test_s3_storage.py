#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
S3 存储模块测试: 用于测试S3/MinIO存储功能
"""

import os
import sys
import logging
import tempfile
import unittest
from pathlib import Path
import uuid
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('s3_storage_test')

# 尝试导入S3存储模块
try:
    from s3_storage import S3Storage
except ImportError:
    logger.error("未能导入S3存储模块，请确保s3_storage.py在当前目录")
    sys.exit(1)

# 加载环境变量
load_dotenv()

class S3StorageTest(unittest.TestCase):
    """测试S3存储功能"""
    
    def setUp(self):
        """测试前准备工作"""
        # 检查必要的环境变量
        required_vars = ['S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.skipTest(f"跳过测试，缺少必要的环境变量: {', '.join(missing_vars)}")
        
        # 创建测试所需的临时文件
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        self.test_txt_path = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_txt_path, "w", encoding="utf-8") as f:
            f.write("这是一个测试文件")
        
        # 创建图片文件（创建一个简单的文本文件模拟图片）
        self.test_img_path = os.path.join(self.temp_dir, "test.jpg")
        with open(self.test_img_path, "w", encoding="utf-8") as f:
            f.write("模拟图片文件内容")
        
        # 初始化S3存储
        try:
            self.s3_storage = S3Storage()
            # 使用唯一的测试前缀，避免干扰生产数据
            self.test_prefix = f"test-{uuid.uuid4().hex[:8]}"
            logger.info(f"测试初始化成功，使用测试前缀: {self.test_prefix}")
        except Exception as e:
            self.fail(f"初始化S3存储失败: {str(e)}")
    
    def tearDown(self):
        """测试后清理工作"""
        # 删除临时文件
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                try:
                    os.remove(file_path)
                except:
                    pass
            try:
                os.rmdir(self.temp_dir)
            except:
                pass
    
    def test_connection(self):
        """测试S3/MinIO连接"""
        try:
            # 尝试检查存储桶是否存在
            result = self.s3_storage.check_bucket_exists()
            self.assertTrue(result, "存储桶检查应返回True")
            logger.info("S3连接测试通过")
        except Exception as e:
            self.fail(f"S3连接测试失败: {str(e)}")
    
    def test_upload_file(self):
        """测试文件上传"""
        try:
            # 上传测试文本文件
            s3_key = f"{self.test_prefix}/test.txt"
            url = self.s3_storage.upload_file(self.test_txt_path, s3_key, "text/plain")
            
            # 验证是否返回了URL
            self.assertIsNotNone(url, "上传文件应返回URL")
            logger.info(f"文件上传测试通过，URL: {url}")
            
            # 打印上传参数，便于调试
            logger.debug(f"上传参数: bucket={self.s3_storage.config['bucket_name']}, key={s3_key}")
            if self.s3_storage.config.get('endpoint_url'):
                logger.debug(f"S3终端节点: {self.s3_storage.config['endpoint_url']}")
            
            # 返回URL，以便查看文件
            return url
        except Exception as e:
            self.fail(f"文件上传测试失败: {str(e)}")
    
    def test_upload_image(self):
        """测试图片上传"""
        try:
            # 上传测试图片文件
            s3_key = f"{self.test_prefix}/test.jpg"
            url = self.s3_storage.upload_file(self.test_img_path, s3_key, "image/jpeg")
            
            # 验证是否返回了URL
            self.assertIsNotNone(url, "上传图片应返回URL")
            logger.info(f"图片上传测试通过，URL: {url}")
            
            # 返回URL，以便查看图片
            return url
        except Exception as e:
            self.fail(f"图片上传测试失败: {str(e)}")
    
    def test_upload_directory(self):
        """测试目录上传"""
        try:
            # 上传测试目录
            result = self.s3_storage.upload_directory(self.temp_dir, self.test_prefix)
            
            # 验证返回的字典中包含上传的文件
            self.assertGreater(len(result), 0, "上传目录应返回至少一个文件的URL")
            logger.info(f"目录上传测试通过，上传了 {len(result)} 个文件")
            
            # 打印URL，以便查看
            for local_path, url in result.items():
                logger.debug(f"上传: {local_path} -> {url}")
            
            return result
        except Exception as e:
            self.fail(f"目录上传测试失败: {str(e)}")

def test_specific_file(file_path, s3_key=None):
    """测试特定文件的上传"""
    # 加载环境变量
    load_dotenv()
    
    # 检查文件存在
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False
    
    # 如果未指定S3键，使用文件名
    if not s3_key:
        s3_key = f"test/{os.path.basename(file_path)}"
    
    try:
        # 初始化S3存储
        s3_storage = S3Storage()
        
        # 从文件扩展名推断内容类型
        _, ext = os.path.splitext(file_path)
        content_type = s3_storage._get_content_type(ext)
        
        # 上传文件
        url = s3_storage.upload_file(file_path, s3_key, content_type)
        
        if url:
            logger.info(f"文件上传成功: {file_path} -> {url}")
            return url
        else:
            logger.error(f"文件上传失败: {file_path}")
            return False
    except Exception as e:
        logger.error(f"文件上传测试异常: {str(e)}")
        return False

def diagnose_s3_config():
    """诊断S3配置问题"""
    # 加载环境变量
    load_dotenv()
    
    # 检查环境变量
    env_vars = {
        'S3_ACCESS_KEY': os.getenv('S3_ACCESS_KEY'),
        'S3_SECRET_KEY': os.getenv('S3_SECRET_KEY'),
        'S3_ENDPOINT_URL': os.getenv('S3_ENDPOINT_URL', '(未设置，使用AWS S3)'),
        'S3_BUCKET': os.getenv('S3_BUCKET'),
        'S3_REGION': os.getenv('S3_REGION', 'us-east-1'),
        'S3_USE_SSL': os.getenv('S3_USE_SSL', 'true'),
        'S3_PUBLIC_URL': os.getenv('S3_PUBLIC_URL', '(未设置)'),
        'S3_PATH_PREFIX': os.getenv('S3_PATH_PREFIX', '(未设置)')
    }
    
    # 输出配置信息（隐藏敏感信息）
    logger.info("===== S3配置诊断 =====")
    for key, value in env_vars.items():
        if key == 'S3_ACCESS_KEY' and value:
            logger.info(f"{key}: {'*' * (len(value) - 4)}{value[-4:]}")
        elif key == 'S3_SECRET_KEY' and value:
            logger.info(f"{key}: {'*' * (len(value) - 4)}{value[-4:]}")
        else:
            logger.info(f"{key}: {value}")
    
    # 检查关键配置
    missing_vars = [k for k, v in env_vars.items() 
                   if k in ['S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET'] and not v]
    
    if missing_vars:
        logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
        return False
    
    # 测试连接
    try:
        s3_storage = S3Storage()
        if s3_storage.check_bucket_exists():
            logger.info("S3连接测试通过")
            return True
        else:
            logger.error("S3连接测试失败：无法访问或创建存储桶")
            return False
    except Exception as e:
        logger.error(f"S3连接测试异常: {str(e)}")
        return False

if __name__ == "__main__":
    # 处理命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--diagnose':
            # 运行诊断
            diagnose_s3_config()
        elif sys.argv[1] == '--test-file' and len(sys.argv) > 2:
            # 测试特定文件
            file_path = sys.argv[2]
            s3_key = sys.argv[3] if len(sys.argv) > 3 else None
            test_specific_file(file_path, s3_key)
        else:
            logger.info("用法: python test_s3_storage.py [--diagnose|--test-file <文件路径> [S3键]]")
    else:
        # 运行所有测试
        unittest.main() 