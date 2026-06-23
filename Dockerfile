FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml .
COPY setup.py .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# 复制项目代码
COPY repomind/ repomind/
COPY readme.md .

# 安装包
RUN pip install --no-cache-dir -e .

# 创建数据目录
RUN mkdir -p /data/repos /data/output

# 暴露端口
EXPOSE 8000 19832

# 默认命令
CMD ["repomind", "web", "--host", "0.0.0.0", "--port", "8000"]
