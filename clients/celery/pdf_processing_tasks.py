#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF处理任务模块
提供PDF转Markdown的Celery任务
"""

import base64
import os
import tempfile
import uuid
import shutil
from typing import Dict, Any, Optional, Union
from datetime import datetime

# 导入Celery应用实例
from .app import celery_app

# 导入MarkMuse相关模块
from markmuse import MarkMuse
from clients.storage import S3Storage
from clients.factory import create_clients
from config import load_api_config, APIConfig
from clients.prompts import PromptManager

# 配置日志
import logging
logger = logging.getLogger(__name__)

@celery_app.task(name="clients.celery.pdf_processing.transcribe_pdf_to_md", bind=True)
def transcribe_pdf_to_md_task(self, 
                             pdf_file_content_base64: str, 
                             original_filename: str, 
                             task_options: Optional[Dict[str, Any]] = None) -> str:
    """
    Celery任务：将PDF转换为Markdown文档（使用base64编码的PDF内容）
    
    工作流程:
    1. 解码PDF内容并保存到临时文件
    2. 将PDF上传到S3
    3. 使用MarkMuse处理S3上的PDF，生成Markdown
    4. 返回生成的Markdown文件的S3 URL
    
    参数:
    - pdf_file_content_base64: PDF文件的Base64编码内容
    - original_filename: 原始PDF文件名，用于生成S3对象键
    - task_options: 可选参数字典，包含：
        - enhance_image: 是否使用AI增强图片理解 (布尔值，默认True)
        - llm_provider: LLM提供商 ('openai'或'qianfan'，默认openai)
        - parallel_images: 并行处理图片的数量 (整数)
    
    返回:
    - str: 生成的Markdown文件的S3 URL
    """
    if task_options is None:
        task_options = {}
    
    temp_pdf_file = None
    temp_markmuse_output_dir = None
    
    try:
        # 1. 加载配置
        app_config: APIConfig = load_api_config()
        
        # 准备MarkMuse使用的S3配置字典
        s3_config_for_markmuse = {
            'access_key': app_config.s3_access_key,
            'secret_key': app_config.s3_secret_key,
            'bucket_name': app_config.s3_bucket,
            'endpoint_url': app_config.s3_endpoint_url,
            'path_prefix': app_config.s3_path_prefix
        }
        
        # 确保所有必要的S3配置都存在
        if not all([s3_config_for_markmuse['access_key'], 
                   s3_config_for_markmuse['secret_key'], 
                   s3_config_for_markmuse['bucket_name']]):
            raise ValueError("S3访问密钥、密钥或存储桶名称未配置")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'status': '正在处理PDF文件'
        })
        
        # 2. 解码并保存PDF到临时文件
        pdf_data = base64.b64decode(pdf_file_content_base64)
        filename_stem, _ = os.path.splitext(original_filename)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"{filename_stem}_") as tmp_file:
            tmp_file.write(pdf_data)
            temp_pdf_file = tmp_file.name
        
        logger.info(f"临时PDF文件已创建: {temp_pdf_file}")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 20,
            'status': '正在上传PDF到S3'
        })
        
        # 3. 初始化S3客户端并上传PDF
        initial_pdf_s3_client = S3Storage(s3_config_for_markmuse)
        
        # 构建PDF在S3上的存储键
        pdf_s3_key = f"incoming_pdfs/{self.request.id}/{uuid.uuid4().hex[:8]}_{original_filename}"
        if s3_config_for_markmuse.get('path_prefix'):
            prefix = s3_config_for_markmuse['path_prefix'].strip('/')
            pdf_s3_key = f"{prefix}/{pdf_s3_key}" if prefix else pdf_s3_key
        
        logger.info(f"正在上传PDF到S3, 键: {pdf_s3_key}")
        pdf_s3_url = initial_pdf_s3_client.upload_file(
            local_file_path=temp_pdf_file,
            remote_path=pdf_s3_key,
            content_type="application/pdf"
        )
        
        if not pdf_s3_url:
            raise RuntimeError(f"上传PDF到S3失败。本地路径: {temp_pdf_file}, S3键: {pdf_s3_key}")
        
        logger.info(f"PDF已上传到S3: {pdf_s3_url}")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 30,
            'status': '初始化MarkMuse处理'
        })
        
        # 4. 准备MarkMuse的临时输出目录
        temp_markmuse_output_dir = tempfile.mkdtemp(prefix="markmuse_output_")
        logger.info(f"MarkMuse临时输出目录: {temp_markmuse_output_dir}")
        
        # 5. 从任务选项中提取MarkMuse参数
        enhance_opt = task_options.get('enhance_image', True) 
        llm_provider_opt = task_options.get('llm_provider', 'openai')
        parallel_images_opt = task_options.get('parallel_images', app_config.parallel_images)
        
        # 6. 为MarkMuse创建OCR和LLM客户端
        clients = create_clients(app_config, llm_provider_opt)
        ocr_client = clients.get("ocr_client")
        llm_client = clients.get("llm_client")
        
        if not ocr_client:
            raise ValueError("无法为MarkMuse创建OCR客户端")
        
        if enhance_opt and not llm_client:
            logger.warning("LLM客户端创建失败，图片增强功能可能受影响")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 40,
            'status': '开始PDF到Markdown的转换'
        })
        
        # 7. 实例化MarkMuse
        converter = MarkMuse(
            ocr_client=ocr_client,
            llm_client=llm_client,
            enhance_images=enhance_opt,
            llm_provider=llm_provider_opt,
            use_s3=True,  # 必须为True，以便MarkMuse将结果上传到S3
            s3_config=s3_config_for_markmuse,
            parallel_images=parallel_images_opt
        )
        
        # 8. 生成输出文件名
        # 使用任务ID和原始文件名的stem部分来确保唯一性
        output_filename_stem = f"processed/{self.request.id}/{filename_stem}_{uuid.uuid4().hex[:4]}"
        
        logger.info(f"调用MarkMuse处理PDF URL: {pdf_s3_url}, 输出stem: {output_filename_stem}")
        
        # 定期更新任务状态的回调函数
        def update_progress(percentage, message):
            progress_value = 40 + int(percentage * 0.5)  # 40-90%范围内
            self.update_state(state='PROGRESS', meta={
                'progress': min(90, progress_value),
                'status': message
            })
        
        # 9. 调用转换方法
        # 注意：此方法应修改为在use_s3=True时返回S3 URL
        markdown_s3_url_or_local_path = converter.convert_pdf_to_md(
            pdf_path_or_url=pdf_s3_url,
            output_dir=temp_markmuse_output_dir,
            output_filename=output_filename_stem,
            is_url=True
        )
        
        # 10. 验证返回是否为S3 URL
        if not isinstance(markdown_s3_url_or_local_path, str) or not markdown_s3_url_or_local_path.startswith(('s3://', 'http://', 'https://')):
            # 如果MarkMuse没有返回S3 URL，尝试获取本地路径并手动上传
            logger.warning(f"MarkMuse未返回有效的S3 URL，收到: {markdown_s3_url_or_local_path}")
            
            # 检查返回是否是本地文件路径
            if isinstance(markdown_s3_url_or_local_path, str) and os.path.isfile(markdown_s3_url_or_local_path):
                logger.info(f"尝试手动上传本地Markdown文件到S3: {markdown_s3_url_or_local_path}")
                
                # 构造S3键
                md_filename = os.path.basename(markdown_s3_url_or_local_path)
                md_s3_key = f"{output_filename_stem}/{md_filename}"
                
                # 上传到S3
                md_s3_url = initial_pdf_s3_client.upload_file(
                    local_file_path=markdown_s3_url_or_local_path,
                    remote_path=md_s3_key,
                    content_type="text/markdown"
                )
                
                if md_s3_url:
                    logger.info(f"手动上传Markdown到S3成功: {md_s3_url}")
                    final_markdown_s3_url = md_s3_url
                else:
                    raise RuntimeError("手动上传Markdown文件到S3失败")
            else:
                raise RuntimeError("MarkMuse未提供Markdown文件的S3 URL或有效的本地路径")
        else:
            final_markdown_s3_url = markdown_s3_url_or_local_path
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 100,
            'status': '转换完成',
            'result': final_markdown_s3_url
        })
        
        logger.info(f"MarkMuse处理完成。Markdown S3 URL: {final_markdown_s3_url}")
        
        # 返回最终的Markdown S3 URL
        return final_markdown_s3_url
    
    except Exception as e:
        logger.error(f"PDF转Markdown任务执行出错: {str(e)}")
        raise
    
    finally:
        # 清理临时PDF文件
        if temp_pdf_file and os.path.exists(temp_pdf_file):
            try:
                os.remove(temp_pdf_file)
                logger.info(f"清理临时PDF文件: {temp_pdf_file}")
            except OSError as e:
                logger.warning(f"无法删除临时PDF文件 {temp_pdf_file}: {e}")
        
        # 清理MarkMuse临时输出目录
        if temp_markmuse_output_dir and os.path.exists(temp_markmuse_output_dir):
            try:
                shutil.rmtree(temp_markmuse_output_dir)
                logger.info(f"清理MarkMuse临时输出目录: {temp_markmuse_output_dir}")
            except Exception as e:
                logger.warning(f"无法完全清理MarkMuse临时目录 {temp_markmuse_output_dir}: {str(e)}")

@celery_app.task(name="clients.celery.pdf_processing.transcribe_pdf_url_to_md", bind=True)
def transcribe_pdf_url_to_md_task(self, 
                                 pdf_s3_url: str,
                                 object_key: str, 
                                 original_filename: str, 
                                 task_options: Optional[Dict[str, Any]] = None) -> str:
    """
    Celery任务：将PDF转换为Markdown文档（使用S3 URL）
    
    工作流程:
    1. 使用MarkMuse直接处理S3上的PDF，生成Markdown
    2. 返回生成的Markdown文件的S3 URL
    
    参数:
    - pdf_s3_url: PDF文件在S3中的URL
    - object_key: PDF文件在S3中的对象键
    - original_filename: 原始PDF文件名，用于生成输出文件名
    - task_options: 可选参数字典，包含：
        - enhance_image: 是否使用AI增强图片理解 (布尔值，默认True)
        - llm_provider: LLM提供商 ('openai'或'qianfan'，默认openai)
        - parallel_images: 并行处理图片的数量 (整数)
    
    返回:
    - str: 生成的Markdown文件的S3 URL
    """
    if task_options is None:
        task_options = {}
    
    temp_markmuse_output_dir = None
    
    try:
        # 1. 加载配置
        app_config: APIConfig = load_api_config()
        
        # 准备MarkMuse使用的S3配置字典
        s3_config_for_markmuse = {
            'access_key': app_config.s3_access_key,
            'secret_key': app_config.s3_secret_key,
            'bucket_name': app_config.s3_bucket,
            'endpoint_url': app_config.s3_endpoint_url,
            'path_prefix': app_config.s3_path_prefix
        }
        
        # 确保所有必要的S3配置都存在
        if not all([s3_config_for_markmuse['access_key'], 
                   s3_config_for_markmuse['secret_key'], 
                   s3_config_for_markmuse['bucket_name']]):
            raise ValueError("S3访问密钥、密钥或存储桶名称未配置")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'status': '开始处理S3上的PDF文件',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 从原始文件名获取基本名称（不含扩展名）
        filename_stem, _ = os.path.splitext(original_filename)
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 20,
            'status': '初始化MarkMuse处理',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 2. 准备MarkMuse的临时输出目录
        temp_markmuse_output_dir = tempfile.mkdtemp(prefix="markmuse_output_")
        logger.info(f"MarkMuse临时输出目录: {temp_markmuse_output_dir}")
        
        # 3. 从任务选项中提取MarkMuse参数
        enhance_opt = task_options.get('enhance_image', True) 
        llm_provider_opt = task_options.get('llm_provider', 'openai')
        parallel_images_opt = task_options.get('parallel_images', app_config.parallel_images)
        
        # 4. 为MarkMuse创建OCR和LLM客户端
        clients = create_clients(app_config, llm_provider_opt)
        ocr_client = clients.get("ocr_client")
        llm_client = clients.get("llm_client")
        
        if not ocr_client:
            raise ValueError("无法为MarkMuse创建OCR客户端")
        
        if enhance_opt and not llm_client:
            logger.warning("LLM客户端创建失败，图片增强功能可能受影响")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 40,
            'status': '开始PDF到Markdown的转换',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 5. 实例化MarkMuse
        converter = MarkMuse(
            ocr_client=ocr_client,
            llm_client=llm_client,
            enhance_images=enhance_opt,
            llm_provider=llm_provider_opt,
            use_s3=True,  # 必须为True，以便MarkMuse将结果上传到S3
            s3_config=s3_config_for_markmuse,
            parallel_images=parallel_images_opt
        )
        
        # 6. 生成输出文件名
        # 使用任务ID和原始文件名的stem部分来确保唯一性
        output_filename_stem = f"processed/{self.request.id}/{filename_stem}_{uuid.uuid4().hex[:4]}"
        
        logger.info(f"调用MarkMuse处理PDF URL: {pdf_s3_url}, 输出stem: {output_filename_stem}")
        
        # 定期更新任务状态的回调函数
        def update_progress(percentage, message):
            progress_value = 40 + int(percentage * 0.5)  # 40-90%范围内
            self.update_state(state='PROGRESS', meta={
                'progress': min(90, progress_value),
                'status': message,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # 7. 调用转换方法
        markdown_s3_url = converter.convert_pdf_to_md(
            pdf_path_or_url=pdf_s3_url,
            output_dir=temp_markmuse_output_dir,
            output_filename=output_filename_stem,
            is_url=True
        )
        
        # 8. 验证返回是否为S3 URL
        if not isinstance(markdown_s3_url, str) or not markdown_s3_url.startswith(('s3://', 'http://', 'https://')):
            # 如果MarkMuse没有返回S3 URL，尝试获取本地路径并手动上传
            logger.warning(f"MarkMuse未返回有效的S3 URL，收到: {markdown_s3_url}")
            
            # 检查返回是否是本地文件路径
            if isinstance(markdown_s3_url, str) and os.path.isfile(markdown_s3_url):
                logger.info(f"尝试手动上传本地Markdown文件到S3: {markdown_s3_url}")
                
                # 初始化S3客户端
                s3_client = S3Storage(s3_config_for_markmuse)
                
                # 构造S3键
                md_filename = os.path.basename(markdown_s3_url)
                md_s3_key = f"{output_filename_stem}/{md_filename}"
                
                # 上传到S3
                md_s3_url = s3_client.upload_file(
                    local_file_path=markdown_s3_url,
                    remote_path=md_s3_key,
                    content_type="text/markdown"
                )
                
                if md_s3_url:
                    logger.info(f"手动上传Markdown到S3成功: {md_s3_url}")
                    final_markdown_s3_url = md_s3_url
                else:
                    raise RuntimeError("手动上传Markdown文件到S3失败")
            else:
                raise RuntimeError("MarkMuse未提供Markdown文件的S3 URL或有效的本地路径")
        else:
            final_markdown_s3_url = markdown_s3_url
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={
            'progress': 100,
            'status': '转换完成',
            'result': final_markdown_s3_url,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"MarkMuse处理完成。Markdown S3 URL: {final_markdown_s3_url}")
        
        # 返回最终的Markdown S3 URL
        return final_markdown_s3_url
    
    except Exception as e:
        logger.error(f"PDF转Markdown任务执行出错: {str(e)}")
        raise
    
    finally:
        # 清理MarkMuse临时输出目录
        if temp_markmuse_output_dir and os.path.exists(temp_markmuse_output_dir):
            try:
                shutil.rmtree(temp_markmuse_output_dir)
                logger.info(f"清理MarkMuse临时输出目录: {temp_markmuse_output_dir}")
            except Exception as e:
                logger.warning(f"无法完全清理MarkMuse临时目录 {temp_markmuse_output_dir}: {str(e)}") 