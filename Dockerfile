FROM python:3.13-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install uv (optional fast installer)
RUN pip install --no-cache-dir uv

COPY requirements.txt /workspace/requirements.txt
# 使用 uv 安裝到系統環境（容器內不另建 venv）
RUN uv pip install --system --no-cache-dir -r /workspace/requirements.txt

COPY . /workspace

# 設定 entrypoint 腳本權限
RUN chmod +x /workspace/scripts/docker-entrypoint.sh

ENV FLASK_APP=run.py \
    MONGO_URI=mongodb://mongo:27017/myDB \
    PORT=8080 \
    HOST=0.0.0.0 \
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2

EXPOSE 8080

# 使用 entrypoint 腳本進行初始化
ENTRYPOINT ["/workspace/scripts/docker-entrypoint.sh"]
# 根據 WORKER_MODE 選擇運行 web 或 worker
CMD ["sh", "-c", "if [ \"$WORKER_MODE\" = \"scheduler\" ]; then python -c 'from app.utils.scheduler import init_scheduler; init_scheduler()'; else gunicorn -w ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --bind ${HOST}:${PORT} --access-logfile - --error-logfile - run:app; fi"]
