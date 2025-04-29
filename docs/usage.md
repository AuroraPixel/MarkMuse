# MarkMuse 使用指南

## 1. 简介

MarkMuse 是一个优雅的 Python 工具，利用 Mistral AI 的 OCR 技术将 PDF 文件转换为 Markdown 格式。支持本地和远程 PDF 转换，提供高质量文档转换效果，并能提取和保存 PDF 中的图片。

## 2. 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

复制 `env.sample` 为 `.env` 并填入必要的 API 密钥：

```
MISTRAL_API_KEY=your_mistral_api_key_here
```

### 基本转换命令

```bash
python markmuse.py --file input.pdf --output-dir output_folder
```

## 3. 基本功能

### 本地 PDF 转换

```bash
python markmuse.py --file input.pdf --output-dir output_folder [--output-name custom_name]
```

### 远程 URL PDF 转换

```bash
python markmuse.py --url https://example.com/document.pdf --output-dir output_folder
```

### 批量转换

```bash
python markmuse.py --batch --input-folder ./pdf文件夹 --output-folder ./md文件夹
```

## 4. 高级功能

### 图片增强

启用 AI 分析 PDF 中的图片内容：

```bash
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image
```

可选择分析提供商（默认为 OpenAI）：
```bash
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image --image-provider qianfan
```

### S3/MinIO 远程存储

将转换结果存储到对象存储服务：

```bash
python markmuse.py --file input.pdf  --use-s3
```

需在 `.env` 中配置：

```
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_KEY=your_s3_secret_key
S3_BUCKET=markmuse
```

### 提示词模板系统

MarkMuse 包含灵活的提示词管理系统，支持 Jinja2 和 LangChain 两种模板引擎：

```python
# 使用提示词管理器
from clients.prompts import PromptManager

manager = PromptManager("path/to/templates")
result = manager.render("template_name", {"变量名": "变量值"})
```

创建自定义模板示例 (Jinja2 格式)：
```
你好，{{ name }}！{% if items %}你有以下物品:{% for item in items %}- {{ item }}{% endfor %}{% endif %}
```

## 5. 参数说明

| 参数 | 说明 |
|------|------|
| `--file` | 本地 PDF 文件路径 |
| `--url` | 远程 PDF 文件 URL |
| `--output-dir` | 输出目录 |
| `--output-name` | 输出文件名 |
| `--batch` | 启用批量转换 |
| `--input-folder` | 批量模式输入文件夹 |
| `--output-folder` | 批量模式输出文件夹 |
| `--enhance-image` | 启用图片分析 |
| `--image-provider` | 图片分析提供商 |
| `--use-s3` | 启用 S3/MinIO 存储 |
| `--debug` | 调试模式 |

## 6. 环境变量配置

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `MISTRAL_API_KEY` | Mistral AI API 密钥 | 必须设置 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 使用图片增强时必须设置 |
| `PARALLEL_IMAGES` | 图片并行处理数量 | 3 |
| `MODEL_NAME` | 图片分析模型 | gpt-4o |
| `S3_*` | S3/MinIO 相关配置 | 使用 S3 存储时设置 |

## 7. 输出与工作原理

### 输出结构

```
输出目录/
├── document.md            # Markdown 文档
└── document_images/       # 提取的图片
    ├── img-0.jpeg
    └── ...
```

### 工作流程

1. **文档处理**：读取 PDF 内容
2. **OCR 处理**：调用 Mistral AI 提取文本和图片
3. **图片处理**：提取图片并保存
4. **Markdown 生成**：创建格式化文档

## 8. 注意事项与常见问题

- API 使用可能产生费用
- 文件大小限制为 50MB
- 需要稳定网络连接
- 大型文件或含大量图片的文件需要更多处理时间
- 检查网络连接和 API 密钥如遇连接问题
- 确保文件路径正确如遇图片显示问题

## 9. 示例命令

```bash
# 基本转换
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output

# 带图片增强的转换
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output --enhance-image

# 使用自定义 API 端点和并行处理
export OPENAI_BASE_URL=https://your-api-endpoint.com/v1
export PARALLEL_IMAGES=5
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image

# S3 存储 + 图片增强组合使用
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image --use-s3
```

## 10. 返回 README

查看[项目首页](../README.md)了解更多信息。 