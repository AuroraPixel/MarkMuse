#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MarkMuse: 将 PDF 文件转换为 Markdown 文档，如同创作的缪斯，为您的文档赋予新生
基于 Mistral AI 的 OCR 技术，企业级优化版本
"""

import os
import sys
import argparse
import base64
import logging
import requests
from pathlib import Path
from tqdm import tqdm
import re
from typing import Optional, Dict, Any, Union
import time
import concurrent.futures

# 导入自定义模块
from config import load_api_config, APIConfig
from clients.ocr import OCRClient
from clients.llm import LLMClient
from clients.storage import S3Storage, StorageError
from clients.factory import create_clients, create_storage_client
from clients.prompts import PromptManager

# 导入S3存储模块
try:
    S3_SUPPORT = True
except ImportError:
    S3_SUPPORT = False
    pass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('markmuse.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('markmuse')

# 加载 API 配置
config = load_api_config()


class MarkMuse:
    """PDF到Markdown转换器类"""
    
    def __init__(
        self, 
        ocr_client: Optional[OCRClient] = None,
        llm_client: Optional[LLMClient] = None,
        enhance_images: bool = False, 
        llm_provider: str = "openai", 
        use_s3: bool = False, 
        s3_config: Dict[str, str] = None,
        parallel_images: int = 3,
        prompt_manager: Optional[PromptManager] = None
    ):
        """
        初始化转换器
        
        参数:
        - ocr_client: OCR 客户端，如果为 None 则尝试创建默认客户端
        - llm_client: LLM 客户端，如果为 None 则尝试创建默认客户端
        - enhance_images: 是否开启图片理解增强
        - llm_provider: LLM 服务提供商 (openai 或 qianfan)
        - use_s3: 是否使用S3存储
        - s3_config: S3配置参数
        - parallel_images: 并行处理图片的数量
        - prompt_manager: 提示词管理器，如果为 None 则创建默认管理器
        """
        # 初始化 OCR 客户端
        self.ocr_client = ocr_client
        
        # 初始化 LLM 客户端
        self.llm_client = llm_client
        
        # 其他参数初始化
        self.enhance_images = enhance_images
        self.parallel_images = parallel_images or config.parallel_images
        
        # 初始化提示词管理器
        self.prompt_manager = prompt_manager or self._create_default_prompt_manager()
        
        # 如果未提供客户端，则尝试创建
        if not self.ocr_client or (enhance_images and not self.llm_client):
            clients = create_clients(config, llm_provider)
            
            # 设置 OCR 客户端
            if not self.ocr_client:
                self.ocr_client = clients["ocr_client"]
                if not self.ocr_client:
                    logger.error("无法创建 OCR 客户端，请检查配置")
            
            # 设置 LLM 客户端
            if not self.llm_client and enhance_images:
                self.llm_client = clients["llm_client"]
                if not self.llm_client:
                    logger.warning("无法创建 LLM 客户端，图片增强功能将不可用")
                    self.enhance_images = False
                elif not self.llm_client.has_capability("image_analysis"):
                    logger.warning(f"{llm_provider} LLM 客户端不支持图片分析功能，图片增强功能将不可用")
                    self.enhance_images = False
                else:
                    logger.info(f"使用 {llm_provider} LLM 客户端作为图片分析工具")
        
        # S3存储相关
        self.use_s3 = use_s3 and S3_SUPPORT
        self.storage_client = None
        
        # 初始化S3存储
        if self.use_s3:
            try:
                # 如果提供了特定配置，则使用它，否则使用全局配置
                s3_config_to_use = s3_config or config
                # 直接创建 S3Storage 实例，而不是通过工厂方法
                if isinstance(s3_config_to_use, dict):
                    self.storage_client = S3Storage(s3_config_to_use)
                else:
                    # 使用 factory 方法创建存储客户端
                    self.storage_client = create_storage_client(s3_config_to_use)
                
                if self.storage_client:
                    logger.info("S3/MinIO存储客户端已初始化")
                else:
                    logger.error("创建S3存储客户端失败")
                    self.use_s3 = False
            except Exception as e:
                logger.error(f"初始化S3存储失败: {str(e)}")
                self.use_s3 = False
    
    def _create_default_prompt_manager(self) -> PromptManager:
        """创建默认提示词管理器"""
        # 使用当前文件所在目录作为基准，创建 prompts 目录
        base_dir = Path(__file__).parent / "prompts"
        os.makedirs(base_dir, exist_ok=True)
        
        # 为不同的模板引擎创建子目录
        for template_type in ["jinja2", "langchain"]:
            os.makedirs(base_dir / template_type, exist_ok=True)
            
        logger.debug(f"创建默认提示词管理器，基础目录: {base_dir}")
        return PromptManager(base_dir=base_dir, default_type="jinja2")
    
    def _get_image_analysis_prompt(self, img_id: str, page_idx: int, page_text: str = "") -> str:
        """
        获取图片分析提示词
        
        参数:
        - img_id: 图片ID
        - page_idx: 页面索引
        - page_text: 页面文本内容
        
        返回:
        - 渲染后的提示词
        """
        try:
            # 检测图片类型（基于图片ID或其他特征）
            if "_chart_" in img_id or "_graph_" in img_id:
                image_type = "chart"
            elif "_diagram_" in img_id or "_flow_" in img_id:
                image_type = "diagram"
            elif "_doc_" in img_id or "_table_" in img_id or "_form_" in img_id:
                image_type = "document"
            else:
                image_type = "general"
            
            # 准备模板参数
            params = {
                "image_type": image_type,
                "page_context": page_text,
                "page_idx": page_idx
            }
            
            # 渲染模板
            prompt = self.prompt_manager.render("image_analysis", params)
            logger.debug(f"为图片 {img_id} 生成提示词，类型: {image_type}")
            return prompt
        except Exception as e:
            logger.warning(f"使用提示词模板失败: {str(e)}，将使用默认提示词")
            # 如果模板渲染失败，使用LLM客户端的默认提示词
            if self.llm_client and hasattr(self.llm_client, 'get_default_prompt'):
                return self.llm_client.get_default_prompt()
            else:
                # 兜底默认提示词
                return ("请详细分析此图片内容，包括但不限于：\n"
                        "1. 图片中的主体对象及其关系\n"
                        "2. 文字信息（如有）\n"
                        "3. 图表数据的解读（如适用）\n"
                        "4. 整体语义理解\n"
                        "输出使用简洁明了的中文描述")
    
    def encode_pdf(self, pdf_path: str) -> Optional[str]:
        """
        将PDF文件编码为base64字符串
        
        参数:
        - pdf_path: PDF文件路径
        
        返回:
        - base64编码的字符串，如果失败则返回None
        """
        try:
            with open(pdf_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode('utf-8')
        except FileNotFoundError:
            logger.error(f"文件不存在: {pdf_path}")
            return None
        except Exception as e:
            logger.error(f"编码PDF时发生错误: {str(e)}")
            return None
    
    def extract_text_from_pdf(self, pdf_path_or_url: str, is_url: bool = False) -> Optional[Any]:
        """
        使用 OCR 客户端从 PDF 中提取文本
        
        参数:
        - pdf_path_or_url: PDF 文件路径或URL
        - is_url: 是否是URL
        
        返回:
        - OCR响应对象，如果失败则返回None
        """
        try:
            if not self.ocr_client:
                logger.error("OCR 客户端未初始化")
                return None
            
            # 处理 S3 存储逻辑
            if self.use_s3 and self.storage_client and not is_url:
                logger.info("使用 S3 模式处理 PDF")
                # 生成唯一存储路径
                filename = Path(pdf_path_or_url).stem
                import uuid
                s3_key = f"pdfs/{filename}/{uuid.uuid4().hex[:8]}.pdf"
                
                # 上传并获取预签名 URL（有效期1小时）
                pdf_url = self.storage_client.upload_file(
                    local_file_path=pdf_path_or_url,
                    remote_path=s3_key,
                    content_type="application/pdf",
                    presign_url=True,
                    expires_in=3600
                )
                
                if not pdf_url:
                    logger.error("PDF上传到S3失败，终止处理")
                    return None
                
                logger.info(f"PDF已上传至S3: {s3_key} (有效期1小时)")
                
                # 使用预签名URL直接处理，不再进行base64编码
                document = {
                    "type": "document_url",
                    "document_url": pdf_url
                }
                
                # 调用 OCR 客户端
                ocr_response = self.ocr_client.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True  # 仍需获取base64图像用于后处理
                )
                
                return ocr_response
                
            # 以下是原有逻辑    
            if is_url:
                logger.info(f"处理远程PDF: {pdf_path_or_url}")
                # 直接使用URL
                document = {
                    "type": "document_url",
                    "document_url": pdf_path_or_url
                }
            else:
                # 本地文件，获取base64编码
                logger.info(f"处理本地PDF: {pdf_path_or_url}")
                base64_pdf = self.encode_pdf(pdf_path_or_url)
                if not base64_pdf:
                    return None
                
                document = {
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{base64_pdf}"
                }
            
            # 调用 OCR 客户端
            ocr_response = self.ocr_client.process(
                model="mistral-ocr-latest",
                document=document,
                include_image_base64=True
            )
            
            return ocr_response
            
        except Exception as e:
            logger.error(f"处理PDF时发生错误: {str(e)}")
            return None
    
    def save_images_from_ocr(self, ocr_response: Any, images_dir: str) -> Dict[str, Union[str, Dict]]:
        """
        从OCR结果中提取并保存图片并支持并行处理
        
        参数:
        - ocr_response: OCR API的响应对象
        - images_dir: 图片保存目录
        
        返回:
        - Dict[str, Union[str, Dict]]: 图片ID到本地保存路径或S3 URL的映射
        """
        # 确保图片目录存在 (即使使用S3也创建本地目录，以应对S3上传失败的情况)
        os.makedirs(images_dir, exist_ok=True)
        
        # 用于存储图片ID到路径的映射
        image_map = {}
        
        # 计算总图片数量
        total_images = 0
        for page in ocr_response.pages:
            if hasattr(page, 'images') and page.images:
                total_images += len(page.images)
        
        if total_images == 0:
            logger.info("未在文档中找到图片")
            return image_map
            
        # 日志输出存储模式
        if self.use_s3 and self.storage_client:
            logger.info(f"使用S3存储处理 {total_images} 张图片 (图片直接上传到S3，不落地本地)")
        else:
            logger.info(f"使用本地存储处理 {total_images} 张图片")
        
        # 存储页面对象，以便在图片处理时获取页面文本
        self._current_pages = ocr_response.pages
        
        # 创建进度条
        with tqdm(total=total_images, desc="处理图片", unit="张") as pbar:
            # 收集所有图片任务
            image_tasks = []
            for page_idx, page in enumerate(ocr_response.pages):
                # 检查页面是否有图片
                if hasattr(page, 'images') and page.images:
                    # 处理页面中的每一张图片
                    for img_idx, img in enumerate(page.images):
                        image_tasks.append((page_idx, img_idx, img))
            
            # 使用线程池进行并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallel_images) as executor:
                futures = {
                    executor.submit(self._process_single_image, task, images_dir): task 
                    for task in image_tasks
                }
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        img_id, img_data = result
                        image_map[img_id] = img_data
                        # 如果原始ID不包含文件扩展名，也添加带扩展名版本到映射
                        if not re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)$', img_id, re.IGNORECASE):
                            image_map[img_id + '.png'] = img_data
                    pbar.update(1)
        
        # 清理暂存的页面对象
        self._current_pages = None
        
        # 日志明确区分结果存储位置
        s3_count = sum(1 for v in image_map.values() if isinstance(v, dict) and v.get("is_s3", False))
        local_count = len(image_map) - s3_count
        
        if s3_count > 0:
            logger.info(f"共提取并上传到S3 {s3_count} 张图片")
        if local_count > 0:
            logger.info(f"共提取并保存到本地 {local_count} 张图片")
            
        return image_map
    
    def _process_single_image(self, task_data, images_dir):
        """处理单张图片并返回结果"""
        page_idx, img_idx, img = task_data
        try:
            # 获取图片ID和base64数据
            img_id = getattr(img, 'id', f"img-p{page_idx+1}-{img_idx+1}.png")
            
            # 安全处理文件名（避免特殊字符）
            safe_filename = re.sub(r"[\\/*?:'\"<>|]", "_", img_id)
            
            # 确保文件名有正确的扩展名
            if not re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)$', safe_filename, re.IGNORECASE):
                safe_filename += '.png'
            
            # 获取base64图像数据
            image_base64_data = getattr(img, 'image_base64', None)
            
            if not image_base64_data:
                return None
            
            # 检查是否包含data URI前缀
            if ',' in image_base64_data and ';base64,' in image_base64_data:
                content_type = image_base64_data.split(';')[0].split(':')[1]
                image_base64_data = image_base64_data.split(',', 1)[1]
            else:
                content_type = "image/png"  # 默认内容类型
            
            try:
                # 清理base64字符串（删除可能的换行符和空白字符）
                cleaned_base64 = ''.join(image_base64_data.split())
                # 解码base64数据
                img_data = base64.b64decode(cleaned_base64)
            except Exception:
                # 尝试填充base64字符串
                try:
                    # 添加缺失的填充字符
                    padding_needed = len(cleaned_base64) % 4
                    if padding_needed:
                        cleaned_base64 += '=' * (4 - padding_needed)
                    img_data = base64.b64decode(cleaned_base64)
                except Exception:
                    return None
            
            # 检查解码后的数据大小，确保不为空
            if len(img_data) < 100:  # 通常任何有效图像都应该>100字节
                return None
                
            img_url = None
            img_path = None
            
            # S3存储路径与URL处理
            if self.use_s3 and self.storage_client:
                # 构建S3存储路径
                parent_dir = Path(images_dir).name  # 获取父目录名
                s3_key = f"{parent_dir}/{safe_filename}"
                
                # 直接上传图片数据到S3
                img_url = self.storage_client.upload_bytes(
                    data=img_data,
                    remote_path=s3_key,
                    content_type=content_type
                )
                
                if img_url:
                    logger.debug(f"图片 {img_id} 已直接上传到S3，URL: {img_url}")
                else:
                    logger.warning(f"图片 {img_id} 上传S3失败，将尝试保存到本地")
            
            # 如果S3上传失败或没有启用S3，则保存到本地
            if not img_url:
                # 创建保存路径
                img_path = os.path.join(images_dir, safe_filename)
                
                # 保存图片
                with open(img_path, 'wb') as f:
                    f.write(img_data)
            
            # 分析图片内容（如果启用增强）
            description = ""
            if self.enhance_images and self.llm_client:
                try:
                    # 获取页面文本内容（如果可用）
                    page_text = ""
                    if hasattr(self, '_current_pages') and self._current_pages and page_idx < len(self._current_pages):
                        page = self._current_pages[page_idx]
                        # 优先获取页面文本，如果没有则尝试从markdown中提取
                        if hasattr(page, 'text'):
                            page_text = page.text
                        elif hasattr(page, 'markdown'):
                            # 从markdown中移除图片链接和格式
                            markdown_text = page.markdown
                            # 移除图片链接
                            markdown_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
                            # 移除标题、加粗等格式
                            markdown_text = re.sub(r'[#*_`~]', '', markdown_text)
                            page_text = markdown_text
                    
                    # 获取图片分析提示词
                    analysis_prompt = self._get_image_analysis_prompt(img_id, page_idx, page_text)
                    
                    # 优先使用 URL 分析，如果支持
                    if img_url and hasattr(self.llm_client, 'analyze_image_url'):
                        description = self.llm_client.analyze_image_url(
                            img_url, 
                            analysis_prompt=analysis_prompt
                        )
                        logger.debug(f"使用URL分析图片 {img_id}")
                    else:
                        # 回退到流式输出分析图片
                        description = self.llm_client.analyze_image_streaming(
                            cleaned_base64, 
                            img_id,
                            analysis_prompt=analysis_prompt
                        )
                        logger.debug(f"使用Base64分析图片 {img_id}")
                    
                    logger.debug(f"图片 {img_id} 分析结果: {description}")
                except Exception as e:
                    logger.error(f"分析图片 {img_id} 时出错: {str(e)}")
            
            # 添加到映射
            if description:
                if img_url:  # S3模式
                    return img_id, {
                        "path": img_url,
                        "description": description,
                        "is_s3": True
                    }
                else:  # 本地模式
                    return img_id, {
                        "path": img_path,
                        "description": description
                    }
            else:
                if img_url:  # S3模式
                    return img_id, {"path": img_url, "is_s3": True}
                else:  # 本地模式
                    return img_id, {"path": img_path}
            
        except Exception as e:
            logger.debug(f"处理图片时出错: {str(e)}")
            return None
    
    def create_markdown_from_ocr(self, ocr_response: Any, output_dir: str, filename: str) -> str:
        """
        从OCR结果创建Markdown文件
        
        参数:
        - ocr_response: OCR API的响应对象
        - output_dir: 输出目录
        - filename: 输出文件名（不含扩展名）
        
        返回:
        - 生成的Markdown文件路径
        """
        # 检查OCR响应是否包含页面
        if not hasattr(ocr_response, 'pages'):
            logger.error("OCR响应中未找到'pages'属性")
            return ""
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建图片目录
        images_dir = os.path.join(output_dir, f"{filename}_images")
        os.makedirs(images_dir, exist_ok=True)
        
        # 保存图片并获取图片ID到路径的映射
        image_map = self.save_images_from_ocr(ocr_response, images_dir)
        
        # 输出Markdown文件的路径
        output_file = os.path.join(output_dir, f"{filename}.md")
        
        # 合并所有页面的Markdown内容
        all_content = []
        
        # 创建页面处理进度条
        with tqdm(total=len(ocr_response.pages), desc="处理页面", unit="页") as pbar:
            for page in ocr_response.pages:
                if hasattr(page, 'markdown'):
                    # 提取页面的Markdown内容
                    page_content = page.markdown
                    
                    # 增强模式：替换图片链接并添加描述
                    if self.enhance_images:
                        # 查找该页面中的所有图片引用
                        img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', page_content)
                        for alt_text, img_url in img_refs:
                            # 从URL中获取图片ID
                            if '/' in img_url:
                                img_id = img_url.split('/')[-1]
                            else:
                                img_id = img_url
                                
                            # 查找图片映射
                            img_info = None
                            if img_id in image_map:
                                img_info = image_map[img_id]
                            # 尝试添加常见图片扩展名
                            elif not re.search(r'\.(jpg|jpeg|png|gif|webp)$', img_id, re.IGNORECASE):
                                for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                                    if img_id + ext in image_map:
                                        img_info = image_map[img_id + ext]
                                        break
                            
                            if img_info and isinstance(img_info, dict) and "description" in img_info:
                                # 获取图片路径或URL
                                img_path_or_url = img_info["path"]
                                
                                # 检查是否是S3路径（使用标记）
                                is_s3 = img_info.get("is_s3", False)
                                
                                # 如果不是S3路径，需要计算相对路径
                                if not is_s3:
                                    img_path_or_url = os.path.relpath(img_path_or_url, output_dir)
                                    img_path_or_url = img_path_or_url.replace(os.sep, '/')
                                
                                # 构建新的Markdown图片引用，带上分析结果
                                description = img_info["description"]
                                new_img_ref = f"![{alt_text}]({img_path_or_url})\n\n**AI图片分析**：{description}\n"
                                
                                # 替换原始引用
                                original_ref = f"![{alt_text}]({img_url})"
                                page_content = page_content.replace(original_ref, new_img_ref)
                    
                    all_content.append(page_content)
                pbar.update(1)
        
        # 合并所有内容
        markdown_content = "\n\n".join(all_content)
        
        def replace_image_link(match):
            """替换图片链接，使其指向本地保存的图片或S3路径"""
            alt_text = match.group(1)
            original_url = match.group(2)
            
            # 从完整的URL中提取图片ID（通常是最后的文件名部分）
            if '/' in original_url:
                img_id = original_url.split('/')[-1]
            else:
                img_id = original_url
            
            # 尝试不同的方式匹配图片ID
            path_or_url = None
            is_s3 = False
            
            # 1. 直接尝试原始ID
            if img_id in image_map:
                img_info = image_map[img_id]
                if isinstance(img_info, dict):
                    path_or_url = img_info["path"]
                    is_s3 = img_info.get("is_s3", False)
                else:
                    path_or_url = img_info
            # 2. 尝试添加常见图片扩展名
            elif not re.search(r'\.(jpg|jpeg|png|gif|webp)$', img_id, re.IGNORECASE):
                for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    if img_id + ext in image_map:
                        img_info = image_map[img_id + ext]
                        if isinstance(img_info, dict):
                            path_or_url = img_info["path"]
                            is_s3 = img_info.get("is_s3", False)
                        else:
                            path_or_url = img_info
                        break
            
            if path_or_url:
                # 如果是S3路径，直接使用URL
                if is_s3:
                    return f"![{alt_text}]({path_or_url})"
                # 否则需要计算相对路径
                else:
                    rel_path = os.path.relpath(path_or_url, output_dir)
                    # 确保路径分隔符是正斜杠（Markdown兼容）
                    rel_path = rel_path.replace(os.sep, '/')
                    return f"![{alt_text}]({rel_path})"
            else:
                return match.group(0)  # 保留原始链接
        
        # 使用正则表达式替换所有图片链接（非增强模式下）
        if not self.enhance_images:
            markdown_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image_link, markdown_content)
        
        # 写入Markdown文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.info(f"转换完成! Markdown文档已保存至 {output_file}")
            
            # 如果启用了S3存储，上传Markdown文件到S3
            final_output_path = output_file  # 默认为本地文件路径
            if self.use_s3 and self.storage_client:
                s3_md_url = self.storage_client.upload_file(output_file, f"{filename}/{filename}.md", "text/markdown")
                if s3_md_url:
                    logger.info(f"Markdown文档已上传到S3/MinIO: {s3_md_url}")
                    final_output_path = s3_md_url  # 使用S3 URL作为返回值
            
            return final_output_path
        except Exception as e:
            logger.error(f"保存Markdown文件时出错: {str(e)}")
            return ""
    
    def convert_pdf_to_md(self, pdf_path_or_url: str, output_dir: str, output_filename: str = None, is_url: bool = False) -> str:
        """
        将PDF文件转换为Markdown文档
        
        参数:
        - pdf_path_or_url: PDF文件路径或URL
        - output_dir: 输出目录
        - output_filename: 输出文件名（不含路径），如果为None则自动生成
        - is_url: 是否是URL
        
        返回:
        - str: 转换成功时返回Markdown文件路径或S3 URL，失败时返回空字符串
        """
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件名
            if not output_filename:
                if is_url:
                    # 从URL获取文件名
                    filename = pdf_path_or_url.split('/')[-1]
                    if not filename or not filename.lower().endswith('.pdf'):
                        filename = "pdf_from_url"
                    else:
                        filename = filename.replace('.pdf', '')
                else:
                    # 从本地路径获取文件名
                    filename = os.path.basename(pdf_path_or_url)
                    filename = os.path.splitext(filename)[0]
            else:
                filename = output_filename
                if filename.lower().endswith('.md'):
                    filename = filename[:-3]
            
            # 提取文本
            ocr_result = self.extract_text_from_pdf(pdf_path_or_url, is_url)
            if ocr_result is None:
                return ""
                
            # 创建Markdown文档并保存图片
            output_path = self.create_markdown_from_ocr(ocr_result, output_dir, filename)
            return output_path
            
        except Exception as e:
            logger.error(f"转换过程中发生错误: {str(e)}")
            return ""

    def batch_convert(self, input_folder: str, output_folder: str) -> None:
        """
        批量转换文件夹中的所有PDF文件为Markdown
        
        参数:
        - input_folder: 输入文件夹
        - output_folder: 输出文件夹
        """
        try:
            # 确保输出文件夹存在
            os.makedirs(output_folder, exist_ok=True)
            
            # 获取所有PDF文件
            pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
            
            if not pdf_files:
                logger.warning(f"在 {input_folder} 中没有找到PDF文件")
                return
            
            logger.info(f"找到 {len(pdf_files)} 个PDF文件待转换")
            
            success_count = 0
            failed_files = []
            
            # 使用tqdm创建进度条
            for pdf_file in tqdm(pdf_files, desc="批量转换", unit="文件"):
                pdf_path = os.path.join(input_folder, pdf_file)
                
                logger.info(f"开始转换 {pdf_file}...")
                output_path = self.convert_pdf_to_md(pdf_path, output_folder)
                if output_path:  # 如果返回了有效路径或URL，则转换成功
                    success_count += 1
                    logger.info(f"PDF '{pdf_file}' 已成功转换，输出: {output_path}")
                else:
                    failed_files.append(pdf_file)
                
                # 添加一些延迟以避免API限制
                time.sleep(1)
            
            # 汇总报告
            logger.info(f"批量转换完成！成功: {success_count}/{len(pdf_files)} 个文件")
            if failed_files:
                logger.warning(f"转换失败的文件: {', '.join(failed_files)}")
                
        except Exception as e:
            logger.error(f"批量转换过程中发生错误: {str(e)}")


def main():
    """
    主函数，处理命令行参数
    """
    parser = argparse.ArgumentParser(description="MarkMuse: 使用 OCR 技术将 PDF 文件转换为 Markdown 文档")
    
    # 添加互斥组 - 不同的转换模式
    group = parser.add_mutually_exclusive_group(required=True)
    
    # 单文件转换参数
    group.add_argument('--file', help="输入的本地 PDF 文件路径")
    group.add_argument('--url', help="输入的远程 PDF 文件URL")
    
    # 输出参数
    parser.add_argument('--output-dir', help="输出目录路径，将在其中保存Markdown文件和图片")
    parser.add_argument('--output-name', help="输出的 Markdown 文件名（可选）")
    
    # 批量转换参数
    group.add_argument('--batch', action='store_true', help="批量转换模式（本地文件）")
    parser.add_argument('--input-folder', help="输入文件夹路径 (批量模式)")
    parser.add_argument('--output-folder', help="输出文件夹路径 (批量模式)")
    
    # 调试选项
    parser.add_argument('--debug', action='store_true', help="启用调试模式，显示详细日志信息")
    
    # 图片理解增强选项
    parser.add_argument('--enhance-image', action='store_true', help="启用图片理解增强功能")
    parser.add_argument('--llm-provider', choices=['openai', 'qianfan'], default='openai', 
                       help="LLM 服务提供商 (openai 或 qianfan)")
    
    # 并行处理选项
    parser.add_argument('--parallel-images', type=int, help="并行处理图片的数量")
    
    # 提示词模板选项
    parser.add_argument('--templates-dir', help="提示词模板目录路径")
    parser.add_argument('--template-type', choices=['jinja2', 'langchain'], default='jinja2',
                        help="提示词模板类型 (jinja2 或 langchain)")
    
    # 新增: S3/MinIO存储选项
    if S3_SUPPORT:
        parser.add_argument('--use-s3', action='store_true', help="启用S3/MinIO远程存储功能")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("调试模式已启用")
    
    # 检查S3支持
    use_s3 = False
    if S3_SUPPORT and hasattr(args, 'use_s3') and args.use_s3:
        use_s3 = True
        # 检查S3环境变量是否设置
        required_s3_vars = ['ACCESS_KEY', 'SECRET_KEY', 'BUCKET']
        missing_vars = [f"S3_{var}" for var in required_s3_vars 
                       if not getattr(config, f"s3_{var.lower()}", None)]
        
        if missing_vars:
            logger.error(f"启用S3/MinIO存储功能失败，缺少必要的环境变量: {', '.join(missing_vars)}")
            logger.error("请在.env文件中设置这些变量，或使用--no-s3禁用S3存储功能")
            sys.exit(1)
        else:
            logger.info("S3/MinIO 环境变量配置已验证")
            
        # 构建 S3 配置字典，供存储客户端使用
        s3_config = {
            'access_key': config.s3_access_key,
            'secret_key': config.s3_secret_key,
            'bucket_name': config.s3_bucket,
            'endpoint_url': config.s3_endpoint_url,
            'path_prefix': config.s3_path_prefix
        }
    else:
        s3_config = None
    
    # 创建客户端
    clients = create_clients(config, args.llm_provider)
    ocr_client = clients["ocr_client"]
    llm_client = clients["llm_client"]
    
    if not ocr_client:
        logger.error("无法创建 OCR 客户端，请检查 API 密钥配置")
        sys.exit(1)
    
    # 如果启用图片增强但未设置对应API密钥，显示警告
    if args.enhance_image:
        if args.llm_provider == 'openai':
            if not config.openai_api_key:
                logger.warning("启用了OpenAI图片理解但未设置OPENAI_API_KEY环境变量")
            elif config.openai_base_url:
                logger.info(f"OpenAI图片理解将使用自定义API端点: {config.openai_base_url}")
            parallel_images = args.parallel_images or config.parallel_images
            logger.info(f"图片并行处理数: {parallel_images}")
        elif args.llm_provider == 'qianfan' and (not config.qianfan_ak or not config.qianfan_sk):
            logger.warning("启用了百度千帆图片理解但未设置QIANFAN_AK或QIANFAN_SK环境变量")
    
    # 如果启用了S3存储，显示信息
    if use_s3:
        endpoint = config.s3_endpoint_url or 'AWS S3'
        bucket = config.s3_bucket
        prefix = config.s3_path_prefix
        logger.info(f"已启用S3/MinIO远程存储，端点: {endpoint}, 存储桶: {bucket}"
                   + (f", 路径前缀: {prefix}" if prefix else ""))
    
    # 创建提示词管理器
    prompt_manager = None
    if args.templates_dir:
        try:
            templates_dir = Path(args.templates_dir)
            if not templates_dir.exists():
                logger.warning(f"指定的提示词模板目录 {args.templates_dir} 不存在，将创建")
                os.makedirs(templates_dir, exist_ok=True)
            
            logger.info(f"使用提示词模板目录: {templates_dir}, 模板类型: {args.template_type}")
            prompt_manager = PromptManager(base_dir=templates_dir, default_type=args.template_type)
        except Exception as e:
            logger.error(f"创建提示词管理器失败: {str(e)}，将使用默认提示词")
    
    try:
        # 处理批量转换（本地文件）
        if args.batch:
            if not args.input_folder or not args.output_folder:
                parser.error("批量模式需要提供 --input-folder 和 --output-folder 参数")
            
            converter = MarkMuse(
                ocr_client=ocr_client,
                llm_client=llm_client,
                enhance_images=args.enhance_image,
                llm_provider=args.llm_provider,
                use_s3=use_s3,
                s3_config=s3_config if isinstance(s3_config, dict) else None,
                parallel_images=args.parallel_images,
                prompt_manager=prompt_manager
            )
            converter.batch_convert(args.input_folder, args.output_folder)
        
        # 处理单文件转换（本地文件）
        elif args.file:
            output_dir = args.output_dir or os.path.dirname(args.file) or os.getcwd()
            
            converter = MarkMuse(
                ocr_client=ocr_client,
                llm_client=llm_client,
                enhance_images=args.enhance_image,
                llm_provider=args.llm_provider,
                use_s3=use_s3,
                s3_config=s3_config if isinstance(s3_config, dict) else None,
                parallel_images=args.parallel_images,
                prompt_manager=prompt_manager
            )
            output_path = converter.convert_pdf_to_md(args.file, output_dir, args.output_name)
            if not output_path:
                logger.error("转换失败")
                sys.exit(1)
            else:
                logger.info(f"转换成功，输出: {output_path}")
        
        # 处理单文件转换（远程URL）
        elif args.url:
            output_dir = args.output_dir or os.getcwd()
            
            converter = MarkMuse(
                ocr_client=ocr_client,
                llm_client=llm_client,
                enhance_images=args.enhance_image,
                llm_provider=args.llm_provider,
                use_s3=use_s3,
                s3_config=s3_config if isinstance(s3_config, dict) else None,
                parallel_images=args.parallel_images,
                prompt_manager=prompt_manager
            )
            output_path = converter.convert_pdf_to_md(args.url, output_dir, args.output_name, is_url=True)
            if not output_path:
                logger.error("转换失败")
                sys.exit(1)
            else:
                logger.info(f"转换成功，输出: {output_path}")
    
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 