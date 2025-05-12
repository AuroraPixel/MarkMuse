"""
API路由定义
提供任务提交和查询接口
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from clients.celery import celery_app
from clients.db.crud import (
    create_task_log,
    get_task_log,
    get_task_logs
)
from clients.storage import S3Storage
from config.api_config import get_db, load_api_config
from .models import (
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskStatusResponse,
    TaskListResponse,
    TaskProgress,
    TaskStatus,
    FileUploadResponse
)

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/tasks",
    tags=["任务"],
    responses={404: {"description": "未找到资源"}},
)


@router.post(
    "/submit",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交任务",
    description="提交一个异步任务到Celery队列执行"
)
async def submit_task(
    request_data: TaskSubmitRequest,
    db: Session = Depends(get_db)
) -> TaskSubmitResponse:
    """
    提交任务接口
    
    接收任务类型和参数，创建Celery任务并返回任务ID
    """
    try:
        # 准备Celery任务参数
        task_kwargs = {}
        if request_data.priority is not None:
            task_kwargs["priority"] = request_data.priority
        if request_data.eta is not None:
            task_kwargs["eta"] = request_data.eta
        if request_data.expires is not None:
            task_kwargs["expires"] = request_data.expires
            
        # 发送任务到Celery
        async_result = celery_app.send_task(
            name=request_data.task_type,
            kwargs=request_data.task_parameters or {},
            **task_kwargs
        )
        
        # 记录任务到数据库
        try:
            create_task_log(
                db=db,
                celery_task_id=async_result.id,
                task_type=request_data.task_type,
                task_parameters=request_data.task_parameters,
                submitted_at=datetime.utcnow()
            )
        except Exception as db_err:
            logger.error(f"记录任务到数据库失败: {db_err}")
            # 即使数据库记录失败，也继续返回任务ID（Celery任务已创建）
        
        # 返回响应
        return TaskSubmitResponse(
            task_id=async_result.id,
            status=TaskStatus(async_result.status),
            message="任务已成功提交"
        )
    except Exception as e:
        logger.error(f"提交任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {str(e)}"
        )


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="查询任务状态",
    description="通过任务ID查询任务状态、进度和结果"
)
async def get_task_status(
    task_id: str = Path(..., description="任务ID"),
    db: Session = Depends(get_db)
) -> TaskStatusResponse:
    """
    查询任务状态接口
    
    通过任务ID查询任务的状态、进度和结果
    结合Celery和数据库中的信息提供完整的任务状态
    """
    try:
        # 从Celery获取任务状态
        celery_result = celery_app.AsyncResult(task_id)
        
        # 从数据库获取任务记录
        db_log = get_task_log(db, task_id)
        
        # 准备响应数据
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus(celery_result.status)
        )
        
        # 添加数据库中的信息（如果有）
        if db_log:
            response.task_type = db_log.task_type
            response.submitted_at = db_log.submitted_at
            response.started_at = db_log.started_at
            response.completed_at = db_log.completed_at
            response.retry_count = db_log.retry_count
            response.worker_name = db_log.worker_name
            
            # 如果Celery结果不可用（可能已过期），使用数据库中的状态
            if celery_result.status == "PENDING" and db_log.status != "PENDING":
                response.status = TaskStatus(db_log.status)
                
                # 如果是成功状态，使用数据库中的结果数据
                if db_log.status == "SUCCESS" and db_log.result_data:
                    response.result = db_log.result_data
                    
                # 如果是失败状态，使用数据库中的错误信息
                elif db_log.status == "FAILURE":
                    response.error_message = db_log.error_message
                    response.traceback = db_log.traceback_info
        
        # 如果Celery有结果数据
        if celery_result.status == "SUCCESS":
            response.result = celery_result.result
        
        # 如果任务失败
        elif celery_result.status == "FAILURE":
            exc = celery_result.result
            response.error_message = str(exc) if exc else None
            response.traceback = celery_result.traceback
        
        # 如果任务有进度信息
        elif celery_result.status == "PROGRESS" and celery_result.info:
            info = celery_result.info
            response.progress = TaskProgress(
                progress=info.get("progress", 0),
                status=info.get("status", ""),
                timestamp=datetime.fromisoformat(info["timestamp"]) 
                    if isinstance(info.get("timestamp"), str) else None
            )
            
        # 如果数据库中有进度信息但Celery中没有
        elif db_log and db_log.status == "PROGRESS" and db_log.result_data:
            info = db_log.result_data
            if isinstance(info, dict) and "progress" in info:
                response.progress = TaskProgress(
                    progress=info.get("progress", 0),
                    status=info.get("status", ""),
                    timestamp=datetime.fromisoformat(info["timestamp"]) 
                        if isinstance(info.get("timestamp"), str) else None
                )
        
        return response
        
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询任务状态失败: {str(e)}"
        )


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="查询任务列表",
    description="查询任务列表，支持分页和过滤"
)
async def get_task_list(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_type: Optional[str] = Query(None, description="按任务类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    days: int = Query(7, ge=1, description="查询最近几天的任务")
) -> TaskListResponse:
    """
    查询任务列表接口
    
    支持分页、按任务类型/状态/时间过滤
    """
    try:
        # 计算时间范围
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 计算分页参数
        skip = (page - 1) * page_size
        
        # 从数据库获取任务列表
        tasks = get_task_logs(
            db=db,
            skip=skip,
            limit=page_size,
            task_type=task_type,
            status=status,
            start_date=start_date
        )
        
        # 计算总数量
        # 注意：这是一个简化的实现，实际应用中可能需要单独查询总数
        total_count = len(tasks)  # 这不是真实的总数，只是当前查询返回的数量
        
        # 转换为响应模型
        task_responses = []
        for task in tasks:
            # 为每个任务创建基本响应
            task_response = TaskStatusResponse(
                task_id=task.celery_task_id,
                task_type=task.task_type,
                status=TaskStatus(task.status),
                submitted_at=task.submitted_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                retry_count=task.retry_count,
                worker_name=task.worker_name
            )
            
            # 如果有结果数据
            if task.status == "SUCCESS" and task.result_data:
                task_response.result = task.result_data
                
            # 如果有错误信息
            elif task.status == "FAILURE":
                task_response.error_message = task.error_message
                task_response.traceback = task.traceback_info
                
            # 添加到列表
            task_responses.append(task_response)
        
        # 返回响应
        return TaskListResponse(
            tasks=task_responses,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"查询任务列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询任务列表失败: {str(e)}"
        )

@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传文件",
    description="上传文件到S3存储，支持多部分表单数据"
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    prefix: str = Form(None, description="存储路径前缀（可选）"),
    db: Session = Depends(get_db)
) -> FileUploadResponse:
    """
    文件上传接口
    
    接收多部分表单数据，将文件上传到S3存储，并返回文件的URL和对象键
    """
    try:
        # 加载配置获取S3参数
        app_config = load_api_config()
        
        # 检查S3配置是否完整
        if not all([app_config.s3_access_key, app_config.s3_secret_key, app_config.s3_bucket]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3存储配置不完整，无法上传文件"
            )
        
        # 准备S3配置
        s3_config = {
            'access_key': app_config.s3_access_key,
            'secret_key': app_config.s3_secret_key,
            'bucket_name': app_config.s3_bucket,
            'endpoint_url': app_config.s3_endpoint_url,
            'path_prefix': app_config.s3_path_prefix
        }
        
        # 初始化S3客户端
        s3_client = S3Storage(s3_config)
        
        # 获取上传文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 确定上传路径和MIME类型
        original_filename = file.filename
        content_type = file.content_type or 'application/octet-stream'
        
        # 生成唯一文件名
        file_ext = os.path.splitext(original_filename)[1]
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{original_filename.replace(' ', '_')}"
        
        # 构建对象键路径
        if prefix:
            object_key = f"{prefix.strip('/')}/{safe_filename}"
        else:
            object_key = f"uploads/{safe_filename}"
        
        # 如果有全局路径前缀，添加到对象键
        if app_config.s3_path_prefix:
            prefix_clean = app_config.s3_path_prefix.strip('/')
            if prefix_clean:
                object_key = f"{prefix_clean}/{object_key}"
        
        # 上传文件到S3
        logger.info(f"上传文件 {original_filename} 到 S3，对象键: {object_key}")
        url = s3_client.upload_bytes(
            data=file_content,
            remote_path=object_key,
            content_type=content_type
        )
        
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="上传文件到S3失败"
            )
        
        # 返回响应
        return FileUploadResponse(
            url=url,
            key=object_key,
            filename=original_filename,
            content_type=content_type,
            file_size=file_size,
            uploaded_at=datetime.utcnow()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传处理失败: {str(e)}"
        )

@router.post(
    "/pdf-to-markdown",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="PDF转Markdown",
    description="上传PDF文件并异步转换为Markdown"
)
async def pdf_to_markdown(
    pdf_file: UploadFile = File(..., description="要转换的PDF文件"),
    enhance_image: bool = Form(True, description="是否使用AI增强图片理解"),
    llm_provider: str = Form("openai", description="LLM提供商，支持'openai'或'qianfan'"),
    parallel_images: Optional[int] = Form(None, description="并行处理图片的数量"),
    db: Session = Depends(get_db)
) -> TaskSubmitResponse:
    """
    PDF转Markdown接口
    
    接收PDF文件，上传到S3，并创建异步任务进行转换处理
    """
    try:
        # 加载配置获取S3参数
        app_config = load_api_config()
        
        # 检查PDF文件类型
        if not pdf_file.content_type or 'pdf' not in pdf_file.content_type.lower():
            logger.warning(f"上传的文件类型可能不是PDF: {pdf_file.content_type}")
        
        # 检查S3配置是否完整
        if not all([app_config.s3_access_key, app_config.s3_secret_key, app_config.s3_bucket]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3存储配置不完整，无法上传文件"
            )
        
        # 准备S3配置
        s3_config = {
            'access_key': app_config.s3_access_key,
            'secret_key': app_config.s3_secret_key,
            'bucket_name': app_config.s3_bucket,
            'endpoint_url': app_config.s3_endpoint_url,
            'path_prefix': app_config.s3_path_prefix
        }
        
        # 初始化S3客户端
        s3_client = S3Storage(s3_config)
        
        # 获取上传文件内容
        pdf_content = await pdf_file.read()
        
        # 确定上传路径和MIME类型
        original_filename = pdf_file.filename
        content_type = pdf_file.content_type or 'application/pdf'
        
        # 生成唯一文件名
        file_ext = os.path.splitext(original_filename)[1]
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{original_filename.replace(' ', '_')}"
        
        # 构建对象键路径
        object_key = f"incoming_pdfs/{safe_filename}"
        
        # 如果有全局路径前缀，添加到对象键
        if app_config.s3_path_prefix:
            prefix_clean = app_config.s3_path_prefix.strip('/')
            if prefix_clean:
                object_key = f"{prefix_clean}/{object_key}"
        
        # 上传文件到S3
        logger.info(f"上传PDF文件 {original_filename} 到 S3，对象键: {object_key}")
        pdf_s3_url = s3_client.upload_bytes(
            data=pdf_content,
            remote_path=object_key,
            content_type=content_type
        )
        
        if not pdf_s3_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="上传PDF文件到S3失败"
            )
        
        # 准备任务参数
        task_parameters = {
            "pdf_s3_url": pdf_s3_url,
            "object_key": object_key,
            "original_filename": original_filename,
            "task_options": {
                "enhance_image": enhance_image,
                "llm_provider": llm_provider
            }
        }
        
        # 如果指定了并行处理图片数量，添加到选项中
        if parallel_images is not None:
            task_parameters["task_options"]["parallel_images"] = parallel_images
        
        # 发送任务到Celery
        async_result = celery_app.send_task(
            name="clients.celery.pdf_processing.transcribe_pdf_url_to_md",
            kwargs=task_parameters
        )
        
        # 记录任务到数据库
        try:
            create_task_log(
                db=db,
                celery_task_id=async_result.id,
                task_type="clients.celery.pdf_processing.transcribe_pdf_url_to_md",
                task_parameters=task_parameters,
                submitted_at=datetime.utcnow()
            )
        except Exception as db_err:
            logger.error(f"记录任务到数据库失败: {db_err}")
            # 即使数据库记录失败，也继续返回任务ID
        
        # 返回响应
        return TaskSubmitResponse(
            task_id=async_result.id,
            status=TaskStatus.PENDING,
            message=f"PDF文件 {original_filename} 已上传并提交转换任务"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF转Markdown处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF转Markdown处理失败: {str(e)}"
        ) 