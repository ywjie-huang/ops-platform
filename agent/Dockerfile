FROM python:3.11-slim

LABEL maintainer="ops-platform"
LABEL description="Docker 容器监控 Agent"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker_agent.py .

EXPOSE 9001 9002

ENV AGENT_PORT=9001
ENV AGENT_WS_PORT=9002

ENTRYPOINT ["python", "docker_agent.py"]

# 构建：docker build -t <你的镜像仓库>/ops-agent:latest .
# 推送：docker push <你的镜像仓库>/ops-agent:latest
