# 基于 Python 官网镜像
FROM ai-asst:1.0.0

# 复制当前目录下的所有文件到容器中的 /app 目录
COPY ./ ./

# 安装依赖
WORKDIR ./
RUN pip install --no-cache-dir -r requirements.txt

# 运行 Flask 应用
CMD ["python", "./ai-asst.py"]

