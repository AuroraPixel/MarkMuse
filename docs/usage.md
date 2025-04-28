# MarkMuse 使用指南

## 简介

MarkMuse 是一个优雅的 Python 工具，如同文档创作的缪斯，利用 Mistral AI 的 OCR 技术将 PDF 文件灵感般地转换为 Markdown 格式。本工具支持本地和远程 URL 的 PDF 文件转换，提供高质量的文档转换效果，并且能够提取和保存 PDF 中的图片。最新版本采用企业级架构设计，提供了完善的错误处理和日志系统。

## 准备工作

### 安装依赖

在使用 MarkMuse 之前，请确保已安装所有依赖项：

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

1. 复制 `env.sample` 文件为 `.env` 文件
2. 在 `.env` 文件中填入您需要的 API 密钥：

```
# 必需的 Mistral AI API 密钥
MISTRAL_API_KEY=your_mistral_api_key_here

# 用于图片分析的 OpenAI API 密钥（可选，仅在使用图片增强功能时需要）
OPENAI_API_KEY=your_openai_api_key_here

# 自定义 OpenAI API 基础 URL（可选）
OPENAI_BASE_URL=your_base_url_here

# 图片并行处理数量（可选，默认为 3）
PARALLEL_IMAGES=3

# 用于百度千帆图片分析（可选，仅在使用千帆作为图片分析提供商时需要）
QIANFAN_AK=your_qianfan_ak_here
QIANFAN_SK=your_qianfan_sk_here
```

您可以在 [Mistral AI 官网](https://mistral.ai/) 注册账号并获取 Mistral API 密钥。

## 基本用法

### 本地 PDF 文件转换

将本地 PDF 文件转换为 Markdown：

```bash
python markmuse.py --file input.pdf --output-dir output_folder
```

如果不指定输出文件名，程序会使用输入文件名作为输出文件名：

```bash
python markmuse.py --file input.pdf --output-dir output_folder --output-name custom_name
```

### 远程 URL PDF 文件转换

将远程 URL 的 PDF 文件转换为 Markdown：

```bash
python markmuse.py --url https://example.com/document.pdf --output-dir output_folder
```

程序会直接从 URL 获取 PDF 内容并进行转换，无需先下载到本地。

### 批量转换本地文件

批量转换文件夹中的所有 PDF 文件：

```bash
python markmuse.py --batch --input-folder <输入文件夹> --output-folder <输出文件夹>
```

参数说明：
- `--batch`：启用批量转换模式
- `--input-folder`：包含 PDF 文件的文件夹路径
- `--output-folder`：保存 Markdown 文件和图片的文件夹路径

示例：
```bash
python markmuse.py --batch --input-folder ./pdf文件夹 --output-folder ./md文件夹
```

### 图片增强功能

MarkMuse 支持对 PDF 中的图片进行智能分析，并将分析结果添加到 Markdown 文档中。要启用此功能，使用 `--enhance-image` 参数：

```bash
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image
```

默认情况下，图片分析使用 OpenAI 的 API。您也可以使用百度千帆作为分析提供商：

```bash
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image --image-provider qianfan
```

#### 图片分析流式输出

当启用图片增强功能时，程序会实时在控制台以流式方式展示图片分析的过程，使您能够直观地了解分析进度和内容。流式输出示例：

```
开始分析图片 img-p1-1.png ...图片是一个简洁的流程图，展示了数据处理的三个主要步骤：数据收集、数据分析和结果展示。
图片中使用了蓝色方框表示各个处理环节，箭头指示了数据流向。
数据收集步骤下方备注了"源自多渠道"，数据分析标注有"AI算法支持"，结果展示标明"可视化展现"。
图中还包含了一些简单的图标：数据收集部分有一个文档图标，数据分析有一个齿轮图标，结果展示有一个图表图标。
图片底部显示了"2023年数据处理标准流程"的文字说明。
图片分析完成
```

#### 图片并行处理

为了提高处理效率，MarkMuse 支持并行处理图片分析任务。默认情况下，程序会同时处理 3 张图片，您可以通过 `PARALLEL_IMAGES` 环境变量调整并行数量：

```
PARALLEL_IMAGES=5  # 设置为同时处理 5 张图片
```

增大并行数量可以提高处理速度，但也会增加 API 调用频率和系统资源消耗。请根据您的 API 限制和系统性能合理设置。

执行时可以看到图片处理的进度条，以及并行处理的日志信息：

```
2023-07-01 10:15:23 - INFO - 图片并行处理数: 5
处理图片: 100%|████████████████████████| 20/20 [00:30<00:00, 0.66张/s]
```

### 调试模式

如果您在使用过程中遇到问题，可以启用调试模式获取更详细的日志信息：

```bash
python markmuse.py --file input.pdf --output-dir output_folder --debug
```

调试模式会显示更详细的处理过程信息，有助于排查问题。

## 完整参数说明

| 参数 | 说明 |
|------|------|
| `--file` | 本地 PDF 文件路径 |
| `--url` | 远程 PDF 文件 URL |
| `--output-dir` | 输出目录，将在其中保存 Markdown 文件和图片 |
| `--output-name` | 输出的 Markdown 文件名（可选，默认使用输入文件名） |
| `--batch` | 启用批量转换模式 |
| `--input-folder` | 批量模式下的输入文件夹路径 |
| `--output-folder` | 批量模式下的输出文件夹路径 |
| `--enhance-image` | 启用图片理解增强功能 |
| `--image-provider` | 图片理解服务提供商，可选 'openai'（默认）或 'qianfan' |
| `--debug` | 启用调试模式，显示详细日志信息 |

## 程序运行界面与日志系统

### 控制台输出

运行程序后，您将看到类似以下的进度显示：

```
2023-06-30 15:42:18 - INFO - 处理本地PDF: ./example.pdf
2023-06-30 15:42:18 - INFO - 图片并行处理数: 3
处理图片: 100%|████████████████████████████████████| 14/14 [00:01<00:00, 13.25张/s]

开始分析图片 img-p1-1.png ...这是一张数据可视化图表，展示了某公司的季度销售数据...
图片分析完成

开始分析图片 img-p2-1.png ...图片显示的是一个组织架构图，从上至下分为三个层级...
图片分析完成

处理页面: 100%|███████████████████████████████████| 7/7 [00:00<00:00, 154.32页/s]
2023-06-30 15:42:45 - INFO - 转换完成! Markdown文档已保存至 output_folder\example.md
```

当启用图片增强功能时，您可以在控制台看到实时的流式图片分析过程。

### 日志文件

除了控制台输出外，程序还会生成一个日志文件 `markmuse.log`，记录详细的处理过程：

```
2023-06-30 15:42:18 - INFO - 处理本地PDF: ./example.pdf
2023-06-30 15:42:18 - INFO - 使用自定义OpenAI API基础URL: https://your-api-endpoint.com/v1
2023-06-30 15:42:18 - INFO - 图片并行处理数: 3
2023-06-30 15:42:20 - INFO - 开始分析图片: img-p1-1.png
2023-06-30 15:42:25 - INFO - 图片 img-p1-1.png 分析完成
2023-06-30 15:42:20 - INFO - 共提取并保存了 14 张图片
2023-06-30 15:42:45 - INFO - 转换完成! Markdown文档已保存至 output_folder\example.md
```

如果发生错误，日志中会记录详细的错误信息，便于排查问题：

```
2023-06-30 15:45:12 - ERROR - 文件不存在: ./不存在的文件.pdf
2023-06-30 15:46:30 - ERROR - Mistral API错误: Invalid API key
```

### 调试模式

使用 `--debug` 参数运行时，程序会输出更详细的日志信息：

```
2023-06-30 15:50:23 - DEBUG - 调试模式已启用
2023-06-30 15:50:23 - INFO - 处理本地PDF: ./example.pdf
2023-06-30 15:50:24 - DEBUG - 正在提取第1页的图片数据
2023-06-30 15:50:24 - DEBUG - 处理图片时出错: 无效的base64数据
...
```

## 输出结构

转换后，程序会生成以下文件结构：

```
输出目录/
├── document.md            # Markdown 文档
└── document_images/       # 包含从 PDF 提取的图片
    ├── img-0.jpeg
    ├── img-1.jpeg
    └── ...
```

在 Markdown 文件中，图片引用已经被自动调整为指向 `document_images/` 目录，格式如下：

```markdown
![图片说明](document_images/img-0.jpeg)
```

这样，您可以直接在 Markdown 查看器中查看文档和图片。

## 工作原理

MarkMuse 使用 Mistral AI 的 OCR 技术进行转换，流程如下：

1. **文档处理**：程序读取本地 PDF 文件或远程 URL 的 PDF 内容
2. **OCR 处理**：调用 Mistral AI 的 OCR API 提取文本、结构信息和图片
3. **图片处理**：
   - 提取所有图片的 base64 编码数据
   - 解码 base64 数据并保存为图片文件
   - 智能处理各种图片格式和 data URI
4. **Markdown 生成**：
   - 根据 OCR 结果创建 Markdown 文档
   - 修正图片引用路径
   - 保留原始文档的格式和结构
5. **日志记录**：
   - 记录处理过程中的关键步骤
   - 记录警告和错误信息
   - 在调试模式下提供详细信息

## 图片处理优化

最新版本改进了图片处理功能：

- **数据 URI 处理**：自动识别和处理包含 data URI 前缀的 base64 数据
- **自动格式检测**：为没有扩展名的图片自动添加适当的扩展名
- **错误恢复**：处理缺少填充字符的 base64 数据
- **文件名安全处理**：移除文件名中的非法字符
- **空数据检测**：自动跳过无效或过小的图片数据
- **多种格式支持**：支持 JPEG、PNG、GIF、WebP、BMP、TIFF 等多种图片格式

## 转换效果

MarkMuse 对以下内容的转换效果良好：
- 文本内容，包括各级标题、段落
- 表格（转换为 Markdown 表格格式）
- 列表（有序列表和无序列表）
- 简单公式
- 图片（自动提取并保存）
- 文档结构和布局

## 错误处理

MarkMuse 采用企业级错误处理机制，能够应对各种异常情况：

1. **API 错误处理**：
   - 区分 API 密钥错误、请求错误和服务器错误
   - 提供有针对性的错误信息和解决建议

2. **文件操作错误**：
   - 处理文件不存在、权限不足等问题
   - 安全地读写文件，避免数据损坏

3. **图片处理错误**：
   - 自动跳过无法处理的图片，保证整体转换流程
   - 详细记录图片处理过程中的问题

4. **网络连接问题**：
   - 优雅处理网络中断和超时
   - 提供清晰的网络错误信息

所有错误都会被记录到日志文件中，便于后续分析和排查。

## 注意事项

1. **API 使用**：使用 Mistral AI API 可能会产生费用，请参考官方文档的定价信息
2. **文件大小**：Mistral AI OCR API 限制上传的文件大小不超过 50MB
3. **网络要求**：使用此工具需要稳定的网络连接，特别是处理远程 URL 时
4. **转换时间**：处理时间取决于 PDF 文件的复杂度、大小和网络速度
5. **URL 格式**：确保 URL 直接指向 PDF 文件，而不是包含 PDF 的网页
6. **输出格式**：某些复杂的格式元素（如复杂的数学公式或特殊图表）可能无法完美转换为 Markdown
7. **图片处理**：图片较多的 PDF 文件会生成较大的输出目录，请确保有足够的磁盘空间
8. **日志文件**：定期检查和清理日志文件，避免占用过多磁盘空间

## 常见问题

### 无法连接到 Mistral API

- 检查您的网络连接
- 确认 API 密钥是否正确
- 检查 Mistral AI 服务是否可用
- 查看日志文件中的详细错误信息

### 图片未正确显示

- 确保 Markdown 查看器支持相对路径的图片引用
- 检查图片文件夹是否与 Markdown 文件位于正确的相对位置
- 检查图片文件是否成功保存
- 启用调试模式查看更详细的图片处理日志

### 特定格式未正确转换

- 复杂表格可能需要手动调整
- 特殊字符或公式可能需要额外处理
- 某些布局可能无法完美保留

### 程序运行缓慢

- 大型 PDF 文件处理需要更多时间
- 包含大量图片的文件需要更多处理时间
- 网络延迟可能影响远程 PDF 的处理速度

## 示例命令

### 转换本地单个文件
```bash
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output
```

### 转换远程 URL
```bash
python markmuse.py --url https://arxiv.org/pdf/2201.04234.pdf --output-dir ./research_papers
```

### 批量转换多个文件
```bash
python markmuse.py --batch --input-folder ./pdf_collection --output-folder ./markdown_collection
```

### 使用调试模式
```bash
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output --debug
```

## 返回 README

查看[项目首页](../README.md)了解更多信息。

## 环境变量配置

除了命令行参数外，MarkMuse 还支持通过环境变量进行配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `MISTRAL_API_KEY` | Mistral AI API 密钥 | 无，必须设置 |
| `OPENAI_API_KEY` | OpenAI API 密钥，用于图片分析 | 无，使用图片增强时必须设置 |
| `OPENAI_BASE_URL` | 自定义 OpenAI API 基础 URL | 无，使用官方端点 |
| `PARALLEL_IMAGES` | 图片并行处理数量 | 3 |
| `MODEL_NAME` | 图片分析使用的模型名称 | gpt-4o |
| `QIANFAN_AK` | 百度千帆 API Access Key | 无，使用千帆图片分析时必须设置 |
| `QIANFAN_SK` | 百度千帆 API Secret Key | 无，使用千帆图片分析时必须设置 |

## 图片分析功能详解

### 流式输出原理

MarkMuse 的图片分析流式输出功能基于 LangChain 框架，能够实时展示 AI 模型的分析过程。具体工作方式如下：

1. 将图片编码为 base64 格式
2. 构造包含图片的请求消息
3. 使用 LangChain 的流式处理接口发送请求
4. 实时接收并显示 AI 模型的分析结果
5. 在控制台中以打字机效果展示分析过程

### 并行处理机制

为了提高处理效率，MarkMuse 采用 Python 的 `concurrent.futures` 库实现图片的并行处理：

1. 首先收集 PDF 中所有图片的信息
2. 创建一个线程池，大小由 `PARALLEL_IMAGES` 环境变量控制
3. 提交所有图片处理任务到线程池
4. 同时处理多张图片的分析任务
5. 使用进度条显示整体完成进度

这种并行处理方式可以显著提高含有大量图片的 PDF 文档处理速度。

### 分析结果集成

图片分析完成后，分析结果会被集成到 Markdown 文档中：

```markdown
![图表标题](example_images/img-p1-1.png)

**AI图片分析**：这是一张数据可视化图表，展示了某公司的季度销售数据。图表包含四个季度的柱状图，其中第三季度销售额最高，达到150万元。图表右侧有详细的数据标注，并用不同颜色区分了各产品线的贡献。
```

这使得生成的 Markdown 文档更加丰富和有价值，特别是对于包含复杂图表或信息图的文档。

## 示例命令

### 基本转换（无图片增强）
```bash
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output
```

### 带图片增强的转换
```bash
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output --enhance-image
```

### 使用自定义 API 端点和并行处理
```bash
# 设置环境变量
export OPENAI_BASE_URL=https://your-api-endpoint.com/v1
export PARALLEL_IMAGES=5

# 执行转换
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output --enhance-image
```

### 使用百度千帆作为图片分析提供商
```bash
python markmuse.py --file ./documents/report.pdf --output-dir ./markdown_output --enhance-image --image-provider qianfan
``` 