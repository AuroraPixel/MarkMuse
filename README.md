# MarkMuse

一个优雅而智能的 PDF 到 Markdown 转换工具，如同创作的缪斯，为您的文档赋予新生。基于 Mistral AI 的 OCR 技术。

## 项目介绍

MarkMuse 是一个使用 Python 开发的创新工具，可以将 PDF 文件优雅地转换为 Markdown 格式。通过利用 Mistral AI 的 OCR（光学字符识别）技术，此工具如同文档创作的Muse，灵感般地保留原始 PDF 的格式、图像和文本布局，生成高质量的 Markdown 文档。

## 功能特点

- 支持本地 PDF 文件和远程 URL 的 PDF 转换
- 支持批量转换多个 PDF 文件
- 保留原始 PDF 的文本格式和布局
- **提取并保存 PDF 中的图片，自动在 Markdown 中正确引用**
- **使用多模态大模型对图片进行增强理解**
- **支持图片分析流式输出和并行处理，提高处理效率**
- **支持将文档和图片存储到S3/MinIO，提供永久链接，便于分享**
- 支持复杂文档的高精度识别
- 利用先进的 OCR 技术处理图像和表格
- 简单易用的命令行界面
- 高效的 Markdown 格式转换

## 技术原理

MarkMuse 使用 Mistral AI 提供的 OCR 和文档理解技术：
- **OCR 处理**：从 PDF 中提取文本，同时保留文档结构和层次
- **图片提取**：保存 PDF 中的图片并在 Markdown 中正确引用
- **格式保留**：识别并保留标题、段落、列表和表格等格式
- **图片分析**：使用 多模态大模型 对图片内容进行智能分析，支持流式输出
- **远程存储**：支持将文档和图片存储到S3兼容的对象存储服务
- **高质量输出**：直接输出结构化的 Markdown 文档
- **错误记录**：全面的日志记录系统，便于问题排查和追踪

## 安装说明

### 环境要求
- Python 3.7 或更高版本
- pip（Python 包管理器）
- Mistral AI API 密钥

### 安装步骤

1. 克隆此仓库：
   ```
   git clone https://github.com/yourusername/markmuse.git
   cd markmuse
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 设置 Mistral AI API 密钥：
   - 复制 `env.sample` 为 `.env` 文件
   - 在 `.env` 文件中添加您的 API 密钥:
   ```
   MISTRAL_API_KEY=your_mistral_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here  # 用于图片分析
   OPENAI_BASE_URL=your_base_url_here       # 可选，自定义 API 端点
   PARALLEL_IMAGES=3                        # 可选，设置图片并行处理数量
   ```

## 使用方法

**详细使用说明请查看[使用指南](docs/usage.md)**

### 常用命令示例

#### 本地 PDF 文件转换

```
python markmuse.py --file input.pdf --output-dir output_folder
```

#### 远程 URL PDF 文件转换

```
python markmuse.py --url https://example.com/document.pdf --output-dir output_folder
```

#### 批量转换本地文件

```
python markmuse.py --batch --input-folder pdf文件夹/ --output-folder md文件夹/
```

#### 启用图片理解增强

```
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image
```

#### 启用S3/MinIO远程存储

```
python markmuse.py --file input.pdf --output-dir output_folder --use-s3
```

#### 组合使用多种功能

```
python markmuse.py --file input.pdf --output-dir output_folder --enhance-image --use-s3
```

## 输出效果

转换后的输出目录结构如下：
```
output_folder/
├── document.md          # 转换后的 Markdown 文件
└── document_images/     # 提取的图片目录
    ├── img-0.jpeg       # 图片文件
    ├── img-1.jpeg
    └── ...
```

在 Markdown 文件中，图片引用格式为：`![图片说明](document_images/img-0.jpeg)`

## 日志系统

程序运行过程中会生成详细的日志信息：
- 控制台输出：显示主要处理步骤和错误
- 日志文件：`markmuse.log` 包含完整的处理记录，便于问题排查
- 调试模式：使用 `--debug` 参数可以获取更详细的日志信息

## 项目结构

项目采用模块化、分层架构设计，主要结构如下：

```
markmuse/
├── clients/           # 客户端目录，存放各种第三方服务的适配器
│   ├── ocr/           # OCR 服务客户端
│   │   ├── abstract_client.py  # OCR 抽象接口
│   │   └── mistral_client.py   # Mistral 实现
│   ├── image/         # 图片分析服务客户端
│   │   ├── abstract_analyzer.py  # 图片分析抽象接口
│   │   ├── openai_analyzer.py    # OpenAI 实现
│   │   └── qianfan_analyzer.py   # 百度千帆实现
│   └── factory.py     # 客户端工厂函数
├── config/            # 配置管理
│   └── api_config.py  # API 配置管理
├── markmuse.py        # 主程序
├── s3_storage.py      # S3/MinIO 存储模块
└── requirements.txt   # 依赖管理
```

## 架构设计

本项目采用了分层架构设计，主要分为以下几层：

1. **接口层**：定义各种服务的抽象接口
2. **实现层**：不同服务提供商的具体实现
3. **工厂层**：负责创建和管理各种服务实例
4. **配置层**：统一管理所有配置
5. **应用层**：核心业务逻辑

这种设计有以下优势：

- **解耦**：核心业务逻辑不直接依赖具体实现
- **可扩展**：轻松添加新的服务提供商支持
- **可测试**：易于进行单元测试和模拟
- **可维护**：每个模块职责清晰，方便维护

## 注意事项

- 本工具需要有效的 Mistral AI API 密钥才能运行
- 使用 API 可能会产生费用，请参考 Mistral AI 的定价
- 处理大型 PDF 文件可能需要更长时间和更多资源
- 转换远程 URL 的 PDF 文件需要稳定的网络连接
- 图片较多的 PDF 文件将会生成较大的输出目录
- 程序会自动处理大多数错误情况，详细信息请查看日志文件

**更多详细使用说明和高级功能，请参阅[使用指南文档](docs/usage.md)**

## 许可证

MIT 