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
from dotenv import load_dotenv
from mistralai import Mistral
import concurrent.futures

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

# 加载环境变量
load_dotenv()

# 获取API密钥
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    logger.error("未设置 MISTRAL_API_KEY 环境变量，请在 .env 文件中设置您的 Mistral API 密钥")
    sys.exit(1)

# 检查图片理解API密钥
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
QIANFAN_AK = os.getenv("QIANFAN_AK")
QIANFAN_SK = os.getenv("QIANFAN_SK")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
# 新增：并行处理图片的数量
PARALLEL_IMAGES = int(os.getenv("PARALLEL_IMAGES", "3"))

# 初始化 Mistral 客户端
client = Mistral(api_key=MISTRAL_API_KEY)


class ImageAnalyzer:
    """多模态图片理解服务类"""
    
    def __init__(self, provider: str = "openai"):
        """
        初始化图片分析器
        
        参数:
        - provider: 服务提供商，支持 'openai' 或 'qianfan'
        """
        self.provider = provider
        self.model = None
        
        if provider == "openai":
            if not OPENAI_API_KEY:
                logger.warning("未设置OPENAI_API_KEY，无法使用OpenAI图片理解功能")
                return
                
            try:
                from langchain_openai import ChatOpenAI
                
                # 构建初始化参数
                model_kwargs = {
                    "model": MODEL_NAME,
                    "max_tokens": None,
                    "api_key": OPENAI_API_KEY,
                    "temperature": 0.1,
                    "max_retries": 3,
                    "timeout": 30,
                    "streaming": True,  # 启用流式输出
                }
                
                # 如果设置了自定义基础URL，则添加到参数中
                if OPENAI_BASE_URL:
                    model_kwargs["base_url"] = OPENAI_BASE_URL
                    logger.info(f"使用自定义OpenAI API基础URL: {OPENAI_BASE_URL}")
                
                self.model = ChatOpenAI(**model_kwargs)
                logger.info("已初始化OpenAI图片理解服务")
            except ImportError:
                logger.error("使用OpenAI需安装langchain-openai，请执行: pip install langchain-openai")
                
        elif provider == "qianfan":
            if not QIANFAN_AK or not QIANFAN_SK:
                logger.warning("未设置QIANFAN_AK或QIANFAN_SK，无法使用百度千帆图片理解功能")
                return
                
            try:
                from langchain_community.llms import QianfanLLMEndpoint
                os.environ["QIANFAN_AK"] = QIANFAN_AK
                os.environ["QIANFAN_SK"] = QIANFAN_SK
                self.model = QianfanLLMEndpoint(model=MODEL_NAME)
                logger.info("已初始化百度千帆图片理解服务")
            except ImportError:
                logger.error("使用千帆需安装langchain-community，请执行: pip install langchain-community")
        else:
            logger.error(f"不支持的提供商: {provider}")
    
    def analyze_image(self, image_base64: str) -> str:
        """分析图片内容 (非流式)"""
        if not self.model:
            return ""
            
        try:
            if self.provider == "openai":
                from langchain_core.messages import HumanMessage
                
                response = self.model.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": "详细描述此图片内容，关注图片中的文字、数据和关键信息，使用中文回复。"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }}
                    ])
                ])
                return response.content
                
            elif self.provider == "qianfan":
                # 百度千帆不支持直接的多模态分析，这里使用其文本能力
                # 实际项目中可以对接百度的其他多模态API
                return "图片分析功能暂不支持千帆接口"
                
            return ""
            
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            return ""
    
    def analyze_image_streaming(self, image_base64: str, img_id: str) -> str:
        """流式分析图片内容并实时输出结果"""
        if not self.model:
            return ""
            
        try:
            if self.provider == "openai":
                from langchain_core.messages import HumanMessage
                
                full_response = ""
                logger.info(f"开始分析图片: {img_id}")
                print(f"\n开始分析图片 {img_id} ...", end="", flush=True)
                
                for chunk in self.model.stream([
                    HumanMessage(content=[
                        {"type": "text", "text": "详细描述此图片内容，关注图片中的文字、数据和关键信息，使用中文回复。"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }}
                    ])
                ]):
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                        full_response += content
                        print(content, end="", flush=True)
                
                print("\n图片分析完成\n", flush=True)
                logger.info(f"图片 {img_id} 分析完成")
                return full_response
                
            elif self.provider == "qianfan":
                return "图片流式分析功能暂不支持千帆接口"
                
            return ""
            
        except Exception as e:
            logger.error(f"图片流式分析失败: {str(e)}")
            return ""


class MarkMuse:
    """PDF到Markdown转换器类"""
    
    def __init__(self, enhance_images: bool = False, image_provider: str = "openai"):
        """
        初始化转换器
        
        参数:
        - enhance_images: 是否开启图片理解增强
        - image_provider: 图片理解服务提供商
        """
        self.client = client
        self.enhance_images = enhance_images
        self.image_analyzer = ImageAnalyzer(image_provider) if enhance_images else None
    
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
        使用 Mistral OCR API 从 PDF 中提取文本
        
        参数:
        - pdf_path_or_url: PDF 文件路径或URL
        - is_url: 是否是URL
        
        返回:
        - OCR响应对象，如果失败则返回None
        """
        try:
            if is_url:
                logger.info(f"处理远程PDF: {pdf_path_or_url}")
                # 直接使用URL
                ocr_response = self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": pdf_path_or_url
                    },
                    include_image_base64=True
                )
            else:
                # 本地文件，获取base64编码
                logger.info(f"处理本地PDF: {pdf_path_or_url}")
                base64_pdf = self.encode_pdf(pdf_path_or_url)
                if not base64_pdf:
                    return None
                    
                # 调用 Mistral OCR API
                ocr_response = self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": f"data:application/pdf;base64,{base64_pdf}"
                    },
                    include_image_base64=True
                )
            
            return ocr_response
            
        except Exception as e:
            # 检查是否是API相关错误
            error_message = str(e).lower()
            if "api key" in error_message or "authentication" in error_message:
                logger.error(f"Mistral API 认证错误: {str(e)}")
            elif "rate limit" in error_message or "too many requests" in error_message:
                logger.error(f"Mistral API 速率限制: {str(e)}")
            elif "server" in error_message or "service" in error_message:
                logger.error(f"Mistral API 服务错误: {str(e)}")
            else:
                logger.error(f"处理PDF时发生错误: {str(e)}")
            return None
    
    def save_images_from_ocr(self, ocr_response: Any, images_dir: str) -> Dict[str, Union[str, Dict]]:
        """
        从OCR结果中提取并保存图片并支持并行处理
        
        参数:
        - ocr_response: OCR API的响应对象
        - images_dir: 图片保存目录
        
        返回:
        - Dict[str, Union[str, Dict]]: 图片ID到本地保存路径的映射，或图片ID到包含路径和描述的字典映射
        """
        # 确保图片目录存在
        os.makedirs(images_dir, exist_ok=True)
        
        # 用于存储图片ID到本地路径的映射
        image_map = {}
        
        # 计算总图片数量
        total_images = 0
        for page in ocr_response.pages:
            if hasattr(page, 'images') and page.images:
                total_images += len(page.images)
        
        if total_images == 0:
            logger.info("未在文档中找到图片")
            return image_map
        
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
            with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL_IMAGES) as executor:
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
        
        logger.info(f"共提取并保存了 {len(image_map)} 张图片")
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
            
            # 创建保存路径
            img_path = os.path.join(images_dir, safe_filename)
            
            # 获取base64图像数据
            image_base64_data = getattr(img, 'image_base64', None)
            
            if not image_base64_data:
                return None
            
            # 检查是否包含data URI前缀
            if ',' in image_base64_data and ';base64,' in image_base64_data:
                image_base64_data = image_base64_data.split(',', 1)[1]
            
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
            
            # 保存图片
            with open(img_path, 'wb') as f:
                f.write(img_data)
            
            # 分析图片内容（如果启用增强）
            description = ""
            if self.enhance_images and self.image_analyzer:
                # 使用流式输出分析图片
                description = self.image_analyzer.analyze_image_streaming(cleaned_base64, img_id)
                logger.debug(f"图片 {img_id} 分析结果: {description}")
            
            # 添加到映射
            if description:
                return img_id, {
                    "path": img_path,
                    "description": description
                }
            else:
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
                                # 计算相对路径
                                img_path = img_info["path"]
                                rel_path = os.path.relpath(img_path, output_dir)
                                rel_path = rel_path.replace(os.sep, '/')
                                
                                # 构建新的Markdown图片引用，带上分析结果
                                description = img_info["description"]
                                new_img_ref = f"![{alt_text}]({rel_path})\n\n**AI图片分析**：{description}\n"
                                
                                # 替换原始引用
                                original_ref = f"![{alt_text}]({img_url})"
                                page_content = page_content.replace(original_ref, new_img_ref)
                    
                    all_content.append(page_content)
                pbar.update(1)
        
        # 合并所有内容
        markdown_content = "\n\n".join(all_content)
        
        def replace_image_link(match):
            """替换图片链接，使其指向本地保存的图片"""
            alt_text = match.group(1)
            original_url = match.group(2)
            
            # 从完整的URL中提取图片ID（通常是最后的文件名部分）
            if '/' in original_url:
                img_id = original_url.split('/')[-1]
            else:
                img_id = original_url
            
            # 尝试不同的方式匹配图片ID
            local_path = None
            
            # 1. 直接尝试原始ID
            if img_id in image_map:
                img_info = image_map[img_id]
                if isinstance(img_info, dict):
                    local_path = img_info["path"]
                else:
                    local_path = img_info
            # 2. 尝试添加常见图片扩展名
            elif not re.search(r'\.(jpg|jpeg|png|gif|webp)$', img_id, re.IGNORECASE):
                for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    if img_id + ext in image_map:
                        img_info = image_map[img_id + ext]
                        if isinstance(img_info, dict):
                            local_path = img_info["path"]
                        else:
                            local_path = img_info
                        break
            
            if local_path:
                # 计算从Markdown文件到图片的相对路径
                rel_path = os.path.relpath(local_path, output_dir)
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
            return output_file
        except Exception as e:
            logger.error(f"保存Markdown文件时出错: {str(e)}")
            return ""
    
    def convert_pdf_to_md(self, pdf_path_or_url: str, output_dir: str, output_filename: str = None, is_url: bool = False) -> bool:
        """
        将PDF文件转换为Markdown文档
        
        参数:
        - pdf_path_or_url: PDF文件路径或URL
        - output_dir: 输出目录
        - output_filename: 输出文件名（不含路径），如果为None则自动生成
        - is_url: 是否是URL
        
        返回:
        - bool: 转换是否成功
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
                return False
                
            # 创建Markdown文档并保存图片
            output_file = self.create_markdown_from_ocr(ocr_result, output_dir, filename)
            return bool(output_file)
            
        except Exception as e:
            logger.error(f"转换过程中发生错误: {str(e)}")
            return False

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
                if self.convert_pdf_to_md(pdf_path, output_folder):
                    success_count += 1
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
    parser = argparse.ArgumentParser(description="MarkMuse: 使用 Mistral AI OCR 将 PDF 文件转换为 Markdown 文档")
    
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
    parser.add_argument('--image-provider', choices=['openai', 'qianfan'], default='openai', 
                       help="图片理解服务提供商 (openai 或 qianfan)")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("调试模式已启用")
    
    # 创建转换器实例
    converter = MarkMuse(
        enhance_images=args.enhance_image,
        image_provider=args.image_provider
    )
    
    # 如果启用图片增强但未设置对应API密钥，显示警告
    if args.enhance_image:
        if args.image_provider == 'openai':
            if not OPENAI_API_KEY:
                logger.warning("启用了OpenAI图片理解但未设置OPENAI_API_KEY环境变量")
            elif OPENAI_BASE_URL:
                logger.info(f"OpenAI图片理解将使用自定义API端点: {OPENAI_BASE_URL}")
            logger.info(f"图片并行处理数: {PARALLEL_IMAGES}")
        elif args.image_provider == 'qianfan' and (not QIANFAN_AK or not QIANFAN_SK):
            logger.warning("启用了百度千帆图片理解但未设置QIANFAN_AK或QIANFAN_SK环境变量")
    
    try:
        # 处理批量转换（本地文件）
        if args.batch:
            if not args.input_folder or not args.output_folder:
                parser.error("批量模式需要提供 --input-folder 和 --output-folder 参数")
            
            converter.batch_convert(args.input_folder, args.output_folder)
        
        # 处理单文件转换（本地文件）
        elif args.file:
            output_dir = args.output_dir or os.path.dirname(args.file) or os.getcwd()
            
            success = converter.convert_pdf_to_md(args.file, output_dir, args.output_name)
            if not success:
                sys.exit(1)
        
        # 处理单文件转换（远程URL）
        elif args.url:
            output_dir = args.output_dir or os.getcwd()
            
            success = converter.convert_pdf_to_md(args.url, output_dir, args.output_name, is_url=True)
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 