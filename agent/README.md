# Docker 容器监控 Agent

轻量级 Agent，部署在 Docker 主机上，暴露 HTTP API 供运维平台拉取容器和系统指标。

## 快速开始

### 1. 从源码构建并发布镜像

在获取本仓库源码的开发机上执行。请将示例镜像地址替换为你自己的镜像仓库：

```bash
cd agent
docker build -t <你的镜像仓库>/ops-agent:latest .
docker login <你的镜像仓库>
docker push <你的镜像仓库>/ops-agent:latest
```

### 2. 在目标 Docker 主机部署 Agent

将 `10.10.20.15` 替换为管理平台能够访问的目标主机管理网 IP：

```bash
docker pull <你的镜像仓库>/ops-agent:latest
docker rm -f ops-agent >/dev/null 2>&1 || true
docker run -d \
  -p 10.10.20.15:9001:9001 \
  --name ops-agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  <你的镜像仓库>/ops-agent:latest
```

> Agent 挂载了 Docker Socket，具备管理宿主机容器的高权限。请在服务器启动参数与防火墙中限制 9001 端口仅允许管理平台访问，不要直接暴露到公网。

### 3. 在平台注册主机

进入 **资产管理 → Docker 监控 → 注册主机**，按向导填写镜像地址和管理网 IP，最后确认 Agent 地址（例如 `10.10.20.15:9001`）并完成注册。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `AGENT_PORT` | 否 | `9001` | 监听端口 |

## API 接口

| 路径 | 说明 |
|------|------|
| `GET /ping` | 健康检查 |
| `GET /info` | 主机系统信息 |
| `GET /containers` | 容器列表及指标 |
| `GET /snapshot` | 一次性返回全部数据（平台用） |
| `GET /containers/{id}/logs?tail=300` | 查看容器最近日志 |
| `GET /containers/{id}/inspect` | 容器完整 inspect 详情（Config/State/挂载/网络等） |
| `POST /containers/{id}/start` | 启动容器 |
| `POST /containers/{id}/stop` | 停止容器 |
| `POST /containers/{id}/restart` | 重启容器 |
| `POST /containers/{id}/delete` | 删除容器（force） |

## 采集内容

- **主机信息**：CPU/内存/磁盘使用率、系统版本、Docker 版本、IP
- **容器列表**：名称、镜像、状态、端口映射（自动发现新增/删除）
- **容器指标**：CPU%、内存使用/限制/百分比、网络 I/O、磁盘 I/O、重启次数
