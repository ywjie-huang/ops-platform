FROM python:3.11-slim

LABEL maintainer="ops-platform"
LABEL description="Docker 容器监控 Agent"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker_agent.py .

EXPOSE 9001

ENV AGENT_PORT=9001

ENTRYPOINT ["python", "docker_agent.py"]

# 构建：docker build -t hub1.lczy.com/public/ops-agent:latest .
# 推送：docker push hub1.lczy.com/public/ops-agent:latest
