# 使用官方 Python 运行时作为父镜像
FROM python:3.12.7

# 设置环境变量，确保 Python 输出直接打印到终端，便于 Docker 日志收集
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 从 AA.env 文件获取的环境变量
# 建议在部署平台（如 Zeabur）的环境变量设置中覆盖这些值，特别是敏感信息
ENV MISTRAL_API_KEY=""
ENV OPENAI_API_KEY=""
ENV OPENAI_BASE_URL="https://chatapi.cortexai.info/v1"
ENV MODLE_NAME="gpt-4o"
ENV S3_ACCESS_KEY=""
ENV S3_SECRET_KEY=""
ENV S3_ENDPOINT_URL="https://s3.ruhlamat.cortexai.info"
ENV S3_BUCKET="markmuse"
ENV S3_REGION=""
ENV S3_USE_SSL="true"
ENV S3_PUBLIC_URL=""
ENV S3_PATH_PREFIX=""
ENV DATABASE_URL="postgresql://user:password@host:port/dbname"
ENV REDIS_URL="redis://host:port"

# Celery 配置 (这些会使用上面定义的 DATABASE_URL 和 REDIS_URL)
# Docker的ENV指令支持这种变量替换
ENV CELERY_BROKER_URL="${REDIS_URL}"
ENV CELERY_RESULT_BACKEND="db+${DATABASE_URL}"
ENV CELERY_TASK_SERIALIZER="json"
ENV CELERY_RESULT_SERIALIZER="json"
ENV CELERY_ACCEPT_CONTENT="json"
ENV CELERY_TIMEZONE="Asia/Shanghai"
ENV CELERY_ENABLE_UTC="true"
ENV CELERY_TASK_TRACK_STARTED="true"
ENV CELERY_TASK_TIME_LIMIT="3600"
ENV CELERY_WORKER_CONCURRENCY="4"

# 复制依赖文件
# 确保你的项目根目录有 requirements.txt 文件
COPY requirements.txt .

# 安装依赖
# 使用 --no-cache-dir 减小镜像体积
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码到工作目录
COPY . .

# 暴露 API 服务端口 (根据 main.py 中的默认设置)
EXPOSE 8000

# 运行 main.py 脚本
# 这将根据 main.py 的默认参数启动 API 和 Worker
CMD ["python", "main.py"] 