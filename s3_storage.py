#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
S3 存储模块: 支持将文件上传到 S3 兼容的存储服务 (AWS S3, MinIO 等)
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, List, Tuple, Union
from pathlib import Path
from urllib.parse import urljoin

# 配置日志
logger = logging.getLogger('markmuse.s3_storage')

class S3Storage:
    """S3 兼容存储服务接口，支持 AWS S3 和 MinIO"""
    
    def __init__(self, config: Dict[str, str] = None):
        """
        初始化 S3 存储客户端
        
        参数:
        - config: 配置字典，如果为 None，则从环境变量读取
        """
        # 从环境变量或配置字典获取 S3 配置
        self.config = config or self._get_config_from_env()
        
        # 检查必要配置
        self._validate_config()
        
        # 创建 S3 客户端
        self.s3_client = self._create_s3_client()
        
        logger.info(f"S3存储模块已初始化，终端点: {self.config.get('endpoint_url', 'AWS默认')}")
    
    def _get_config_from_env(self) -> Dict[str, str]:
        """从环境变量获取 S3 配置"""
        return {
            'access_key': os.getenv('S3_ACCESS_KEY', ''),
            'secret_key': os.getenv('S3_SECRET_KEY', ''),
            'endpoint_url': os.getenv('S3_ENDPOINT_URL', ''),
            'region_name': os.getenv('S3_REGION', 'us-east-1'),
            'bucket_name': os.getenv('S3_BUCKET', ''),
            'use_ssl': os.getenv('S3_USE_SSL', 'true').lower() == 'true',
            'public_url_base': os.getenv('S3_PUBLIC_URL', ''),
            'path_prefix': os.getenv('S3_PATH_PREFIX', '')
        }
    
    def _validate_config(self) -> None:
        """验证 S3 配置的有效性"""
        required_fields = ['access_key', 'secret_key', 'bucket_name']
        
        # 配置校验
        errors = []
        for field in required_fields:
            if not self.config.get(field):
                errors.append(f"缺少必要的S3配置: {field}")
        
        # 如果有错误，记录日志并抛出异常
        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError(f"S3配置错误: {', '.join(errors)}")
    
    def _create_s3_client(self):
        """创建 S3 客户端"""
        # 获取配置
        access_key = self.config['access_key']
        secret_key = self.config['secret_key']
        endpoint_url = self.config.get('endpoint_url')  # 对于 AWS S3 可为空
        region_name = self.config.get('region_name')
        use_ssl = self.config.get('use_ssl', True)
        
        # 创建 S3 客户端
        try:
            s3_client_args = {
                'aws_access_key_id': access_key,
                'aws_secret_access_key': secret_key,
                'region_name': region_name
            }
            
            # 如果设置了自定义端点 (MinIO)，则添加到参数
            if endpoint_url:
                s3_client_args.update({
                    'endpoint_url': endpoint_url,
                    'use_ssl': use_ssl
                })
                # 对于 MinIO，通常我们不需要设置签名版本
                if 'minio' in endpoint_url.lower():
                    s3_client_args['config'] = boto3.session.Config(
                        signature_version='s3v4',  # MinIO 支持 S3v4 签名
                        s3={'addressing_style': 'path'}  # 路径样式 URL
                    )
            
            return boto3.client('s3', **s3_client_args)
            
        except Exception as e:
            logger.error(f"创建 S3 客户端失败: {str(e)}")
            raise
    
    def check_bucket_exists(self) -> bool:
        """检查存储桶是否存在，不存在则创建"""
        bucket_name = self.config['bucket_name']
        
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"存储桶 {bucket_name} 已存在")
            return True
        except ClientError as e:
            # 如果桶不存在，则创建
            if e.response['Error']['Code'] == '404':
                try:
                    # 创建桶的参数
                    create_args = {'Bucket': bucket_name}
                    
                    # 如果不是 AWS S3，不需要指定区域
                    if self.config.get('endpoint_url'):
                        self.s3_client.create_bucket(**create_args)
                    else:
                        # AWS S3 创建桶需要区域配置
                        region = self.config['region_name']
                        location_constraint = {'LocationConstraint': region}
                        create_args['CreateBucketConfiguration'] = location_constraint
                        self.s3_client.create_bucket(**create_args)
                    
                    logger.info(f"创建存储桶 {bucket_name} 成功")
                    return True
                except Exception as create_error:
                    logger.error(f"创建存储桶 {bucket_name} 失败: {str(create_error)}")
                    return False
            # 其他错误
            else:
                logger.error(f"检查存储桶 {bucket_name} 时出错: {str(e)}")
                return False
    
    def upload_file(self, local_file_path: str, s3_key: str = None, content_type: str = None) -> Optional[str]:
        """
        上传文件到 S3 存储
        
        参数:
        - local_file_path: 本地文件路径
        - s3_key: S3 中的对象键(路径)，如果为 None，则使用文件名
        - content_type: 文件内容类型
        
        返回:
        - 文件的公共URL，如果上传失败返回None
        """
        bucket_name = self.config['bucket_name']
        
        # 检查桶是否存在
        if not self.check_bucket_exists():
            return None
        
        try:
            # 检查文件是否存在
            if not os.path.exists(local_file_path):
                logger.error(f"要上传的文件不存在: {local_file_path}")
                return None
            
            # 如果没有指定 S3 键，则使用文件名
            if not s3_key:
                file_name = os.path.basename(local_file_path)
                path_prefix = self.config.get('path_prefix', '').strip('/')
                s3_key = f"{path_prefix}/{file_name}" if path_prefix else file_name
            
            # 修正: 直接使用boto3的upload_file而不是upload_fileobj
            extra_args = {}
            
            # 如果提供了内容类型，则添加到参数
            if content_type:
                extra_args['ContentType'] = content_type
                
            # 额外参数：使文件公开可访问
            extra_args['ACL'] = 'public-read'
            
            # 使用upload_file方法代替upload_fileobj
            logger.debug(f"正在上传文件 {local_file_path} 到 {bucket_name}/{s3_key}")
            self.s3_client.upload_file(
                Filename=local_file_path,
                Bucket=bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"文件 {local_file_path} 上传到 S3 成功，对象键: {s3_key}")
            
            # 生成公共 URL
            public_url = self.get_public_url(s3_key)
            return public_url
            
        except Exception as e:
            logger.error(f"上传文件 {local_file_path} 到 S3 失败: {str(e)}")
            import traceback
            logger.debug(f"错误详情: {traceback.format_exc()}")
            return None
    
    def get_public_url(self, s3_key: str) -> str:
        """
        获取对象的公共 URL
        
        参数:
        - s3_key: S3 中的对象键(路径)
        
        返回:
        - 对象的公共URL
        """
        # 如果配置了公共URL基础地址，则使用它
        public_url_base = self.config.get('public_url_base')
        bucket_name = self.config['bucket_name']
        
        if public_url_base:
            # 确保 URL 以斜杠结尾
            if not public_url_base.endswith('/'):
                public_url_base += '/'
            
            # 构建完整 URL
            return urljoin(public_url_base, s3_key)
        else:
            # 否则使用 S3 端点构建 URL
            endpoint_url = self.config.get('endpoint_url')
            
            # AWS S3 的默认 URL 格式
            if not endpoint_url:
                region = self.config.get('region_name', 'us-east-1')
                return f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
            
            # 自定义端点 (如 MinIO) 的 URL 格式
            # 移除协议前缀，避免 urljoin 替换整个 URL
            if endpoint_url.startswith('http://'):
                clean_endpoint = endpoint_url[7:]
            elif endpoint_url.startswith('https://'):
                clean_endpoint = endpoint_url[8:]
            else:
                clean_endpoint = endpoint_url
            
            # 确保端点以斜杠结尾
            if not clean_endpoint.endswith('/'):
                clean_endpoint += '/'
                
            # 构建完整 URL
            protocol = 'https' if self.config.get('use_ssl', True) else 'http'
            return f"{protocol}://{clean_endpoint}{bucket_name}/{s3_key}"
    
    def upload_directory(self, local_dir: str, s3_prefix: str = "") -> Dict[str, str]:
        """
        上传整个目录到 S3 存储
        
        参数:
        - local_dir: 本地目录路径
        - s3_prefix: S3 中的路径前缀
        
        返回:
        - 字典，键为本地文件路径，值为 S3 公共URL
        """
        result = {}
        path_prefix = self.config.get('path_prefix', '').strip('/')
        
        # 构建完整的 S3 前缀
        if path_prefix:
            if s3_prefix:
                full_prefix = f"{path_prefix}/{s3_prefix}"
            else:
                full_prefix = path_prefix
        else:
            full_prefix = s3_prefix
        
        # 递归上传目录中的所有文件
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                
                # 计算文件的相对路径
                rel_path = os.path.relpath(local_file_path, local_dir)
                
                # 构建 S3 对象键
                if full_prefix:
                    s3_key = f"{full_prefix}/{rel_path}"
                else:
                    s3_key = rel_path
                
                # 处理 Windows 路径分隔符
                s3_key = s3_key.replace('\\', '/')
                
                # 根据文件扩展名确定内容类型
                _, ext = os.path.splitext(file)
                content_type = self._get_content_type(ext)
                
                # 上传文件
                public_url = self.upload_file(local_file_path, s3_key, content_type)
                if public_url:
                    result[local_file_path] = public_url
        
        return result
    
    def _get_content_type(self, ext: str) -> str:
        """根据文件扩展名获取内容类型"""
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.js': 'application/javascript',
            '.css': 'text/css'
        }
        
        return content_types.get(ext.lower(), 'application/octet-stream') 