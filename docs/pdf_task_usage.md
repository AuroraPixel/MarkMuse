# PDF转Markdown任务使用指南

本文档介绍如何使用`clients.celery.pdf_processing.transcribe_pdf_to_md`任务将PDF文件转换为Markdown格式并存储到S3。

## 功能简介

该Celery任务接收PDF文件内容，将其上传到S3，然后使用MarkMuse进行处理，生成Markdown文档并返回该文档的S3 URL。任务支持图片理解增强，可选择不同的LLM提供商。

## 任务参数

任务接受以下参数：

- `pdf_file_content_base64`: PDF文件的Base64编码内容（必需）
- `original_filename`: 原始PDF文件名，用于生成S3对象名（必需）
- `task_options`: 可选参数字典，包含：
  - `enhance_image`: 是否使用AI分析图片内容（布尔值，默认`True`）
  - `llm_provider`: LLM提供商（`openai`或`qianfan`，默认`openai`）
  - `parallel_images`: 并行处理图片的数量（整数，可选）

## 返回值

任务成功完成后返回转换生成的Markdown文件的S3 URL。

## 使用方法

### 通过API提交任务

```python
import requests
import base64

# API端点
API_URL = "http://localhost:8000/tasks/submit"

# 读取PDF文件并编码
with open("example.pdf", "rb") as f:
    pdf_content = f.read()
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

# 构建请求数据
payload = {
    "task_type": "clients.celery.pdf_processing.transcribe_pdf_to_md",
    "task_parameters": {
        "pdf_file_content_base64": pdf_base64,
        "original_filename": "example.pdf",
        "task_options": {
            "enhance_image": True,
            "llm_provider": "openai"
        }
    }
}

# 发送请求
response = requests.post(API_URL, json=payload)
response_data = response.json()

# 获取任务ID
task_id = response_data.get("task_id")
print(f"任务已提交，ID: {task_id}")
```

### 查询任务状态

```python
import requests

# 任务ID
task_id = "your_task_id_here"

# 状态API
STATUS_URL = f"http://localhost:8000/tasks/{task_id}/status"

# 获取状态
response = requests.get(STATUS_URL)
status_data = response.json()

# 输出状态
print(f"任务状态: {status_data.get('status')}")

# 如果任务完成，获取结果
if status_data.get("status") == "SUCCESS":
    markdown_url = status_data.get("result")
    print(f"Markdown文件URL: {markdown_url}")
```

## 使用测试脚本

项目提供了测试脚本`tests/test_pdf_task.py`来简化任务测试：

```bash
# 基本用法
python tests/test_pdf_task.py /path/to/your/document.pdf

# 指定不使用图片增强
python tests/test_pdf_task.py /path/to/your/document.pdf false

# 指定LLM提供商
python tests/test_pdf_task.py /path/to/your/document.pdf true qianfan
```

## 环境配置要求

- 确保S3/MinIO配置正确
  - `S3_ACCESS_KEY`
  - `S3_SECRET_KEY`
  - `S3_BUCKET`
  - `S3_ENDPOINT_URL`（可选）
  - `S3_PATH_PREFIX`（可选）

- 确保OCR和LLM API配置正确
  - `MISTRAL_API_KEY`：用于OCR处理
  - `OPENAI_API_KEY`或`QIANFAN_AK`/`QIANFAN_SK`：用于图片分析（如果启用增强）

## 任务处理流程

1. 接收PDF内容和文件名
2. 将PDF内容解码并保存到临时文件
3. 上传PDF到S3
4. 创建MarkMuse实例并配置相关参数
5. 调用MarkMuse处理PDF，生成Markdown并保存图片
6. 返回生成的Markdown文件S3 URL
7. 清理临时文件和目录

## 常见问题

1. **任务提交后状态一直为`PENDING`**
   
   检查Celery worker是否正在运行。启动worker：
   ```bash
   celery -A clients.celery.app worker --loglevel=info
   ```

2. **任务失败并显示S3相关错误**
   
   检查S3配置是否正确，存储桶是否存在，权限是否设置正确。

3. **使用图片增强但任务失败**
   
   检查相应的LLM API密钥是否正确配置。如使用OpenAI，需要配置`OPENAI_API_KEY`；使用千帆，需要配置`QIANFAN_AK`和`QIANFAN_SK`。 