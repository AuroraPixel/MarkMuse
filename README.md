# 通用任务队列API

基于Celery、Redis和PostgreSQL的通用任务队列Web API，提供异步任务的提交、执行和状态查询功能。

## 功能特点

- 提供基于FastAPI的RESTful API接口
- 支持任务状态的持久化存储和查询
- 自动记录任务执行过程、状态和结果
- 支持任务进度实时跟踪
- 支持任务重试和错误处理
- 提供完整的任务审计日志

## 系统架构

- **FastAPI**: 提供Web API接口
- **Celery**: 分布式任务队列
- **Redis**: 作为Celery的消息代理和结果后端
- **PostgreSQL**: 持久化存储任务状态和结果

## 快速开始

### 环境要求

- Python 3.8+
- PostgreSQL 12+
- Redis 6+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建一个`.env`文件，配置以下环境变量：

```
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/taskapi

# Redis配置
REDIS_URL=redis://localhost:6379/0

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 启动服务

使用 `main.py` 脚本统一启动 API 服务和 Celery Worker：

```bash
python main.py
```

默认情况下，这将同时启动 API 服务和 Celery Worker。您可以通过命令行参数自定义行为：

- **同时启动 API 和 Worker (默认)**:
  ```bash
  python main.py
  ```

- **仅启动 API 服务**:
  ```bash
  python main.py --no-worker
  ```
  或者，更明确地：
  ```bash
  python main.py --run-api --no-worker
  ```

- **仅启动 Celery Worker**:
  ```bash
  python main.py --no-api
  ```
  或者，更明确地：
  ```bash
  python main.py --run-worker --no-api
  ```

- **自定义 API 服务端口和启用热重载**:
  ```bash
  python main.py --api-port 8080 --api-reload
  ```

- **自定义 Worker 并发数和日志级别**:
  ```bash
  python main.py --worker-concurrency 8 --worker-loglevel debug
  ```

- **启用全局调试模式**:
  ```bash
  python main.py --debug
  ```

更多可用参数，请运行：
```bash
python main.py --help
```

## API接口说明

### 提交任务

```
POST /tasks/submit
```

**请求体示例：**

```json
{
  "task_type": "clients.celery.example_tasks.process_document",
  "task_parameters": {
    "document_id": "doc-123",
    "options": {
      "format": "pdf",
      "quality": "high"
    }
  }
}
```

**响应示例：**

```json
{
  "task_id": "8f8e3d3a-7b1e-4fee-b1cb-7d8a9ca0e369",
  "status": "PENDING",
  "message": "任务已成功提交"
}
```

### 查询任务状态

```
GET /tasks/{task_id}/status
```

**响应示例：**

```json
{
  "task_id": "8f8e3d3a-7b1e-4fee-b1cb-7d8a9ca0e369",
  "task_type": "clients.celery.example_tasks.process_document",
  "status": "SUCCESS",
  "submitted_at": "2023-11-05T12:00:00Z",
  "started_at": "2023-11-05T12:00:05Z",
  "completed_at": "2023-11-05T12:00:15Z",
  "progress": {
    "progress": 100,
    "status": "任务完成",
    "timestamp": "2023-11-05T12:00:15Z"
  },
  "result": {
    "document_id": "doc-123",
    "status": "completed",
    "pages_processed": 15,
    "processing_time": 5.2
  }
}
```

### 查询任务列表

```
GET /tasks/?page=1&page_size=10&task_type=process_document&status=SUCCESS
```

**响应示例：**

```json
{
  "tasks": [
    {
      "task_id": "8f8e3d3a-7b1e-4fee-b1cb-7d8a9ca0e369",
      "task_type": "clients.celery.example_tasks.process_document",
      "status": "SUCCESS",
      "submitted_at": "2023-11-05T12:00:00Z",
      "completed_at": "2023-11-05T12:00:15Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 10
}
```

## 测试

运行测试脚本来测试API功能：

```bash
python test_task_api.py
```

## 自定义任务

要创建自定义任务，只需继承`DatabaseAwareTask`基类：

```python
from celery import shared_task
from clients.celery.base_tasks import DatabaseAwareTask

@shared_task(bind=True, base=DatabaseAwareTask)
def my_custom_task(self, param1, param2):
    # 更新进度
    self.update_progress(0, "任务开始")
    
    # 执行任务逻辑
    # ...
    
    # 完成任务
    self.update_progress(100, "任务完成")
    
    # 返回结果
    return {"status": "success", "data": result_data}
```

## 许可证

MIT 

## 欢迎加了群聊
![图片](https://s3.cortexai.info/open/wc.jpg)
