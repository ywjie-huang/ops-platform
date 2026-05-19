# Docker 容器监控 Agent

轻量级 Agent，部署在 Docker 主机上，暴露 HTTP API 供运维平台拉取容器和系统指标。

## 快速开始

### 1. 在目标机器启动 Agent

```bash
docker run -d -p 9001:9001 \
  --name ops-agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  hub1.lczy.com/public/ops-agent:latest
```

### 2. 在平台注册主机

进入 **资产管理 → Docker 监控 → 注册主机**，填写名称和 Agent 地址（`目标IP:9001`）即可。

## 构建镜像

```bash
docker build -t hub1.lczy.com/public/ops-agent:latest .
docker push hub1.lczy.com/public/ops-agent:latest
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `AGENT_PORT` | ❌ | `9001` | 监听端口 |

## API 接口

| 路径 | 说明 |
|------|------|
| `GET /ping` | 健康检查 |
| `GET /info` | 主机系统信息 |
| `GET /containers` | 容器列表及指标 |
| `GET /snapshot` | 一次性返回全部数据（平台用） |

## 采集内容

- **主机信息**：CPU/内存/磁盘使用率、系统版本、Docker 版本、IP
- **容器列表**：名称、镜像、状态、端口映射（自动发现新增/删除）
- **容器指标**：CPU%、内存使用/限制/百分比、网络 I/O、磁盘 I/O、重启次数
