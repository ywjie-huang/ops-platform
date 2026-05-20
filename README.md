# my-project · 运维管理平台

基于 **FastAPI + Vue 3 + Element Plus + MySQL** 的企业级运维管理平台，纯前后端分离架构，集成 **Prometheus + Alertmanager + Kubernetes** 实现主机监控、告警管理与容器资源自动发现。

---

## 导航结构

| 一级分组 | 二级菜单 | 说明 |
|---------|---------|------|
| **报表大屏** | 仪表盘 / 报表中心 | 系统概览 + 预置报表/自定义报表/CSV导出 |
| **资产管理** | 主机管理 / 主机密钥 / 容器管理 / Docker 监控 | 资产台账 + SSH 密钥管理 + SSH 终端(含SFTP) + K8s 集群自动发现 + Docker Agent 主机监控 |
| **监控告警** | 主机监控 / 告警规则 / 告警事件 / 告警管理 | Prometheus 实时数据 + 告警规则 + Alertmanager 事件 + 告警处理 |
| **工单协作** | 工单协作 | 工单流转 |
| **批量执行** | 批量执行 | SSH 批量命令执行 + 实时输出 + 执行历史 |
| **巡检中心** | 巡检报告 / 阈值配置 | 主机/K8s/资产自动巡检 + 报告管理 + 滑块式阈值配置 + 快捷预设 |
| **用户管理** | 用户管理 / 角色权限 | RBAC 权限 + 菜单权限分配 |
| **系统管理** | 审计日志 / 配置中心 | 操作审计 + Prometheus/Alertmanager 地址配置 |

---

## 核心功能

### 1. 认证与账号

- 登录页（暗色渐变背景 + 玻璃拟态卡片 + 动态装饰）
- **图形验证码**：4 位数字验证码，点击可刷新，120 秒过期，登录失败自动刷新
- 错误提示区分：登录页显示具体错误（账号或密码不正确 / 验证码错误），其他页面 Token 过期显示"登录已过期"
- 基于 MySQL 的用户表，`pbkdf2_sha256` 密码哈希
- 首次启动自动创建默认管理员
- 修改密码：右上角用户菜单 → 弹窗修改，修改后需重新登录

### 2. 主机管理（资产管理）

- 资产新增、删除（列表页弹窗表单）
- 资产详情页：查看完整信息 + 编辑（含 SSH 配置）
- 字段：名称、IP、类型、规格、系统、状态、负责人、描述
- 资产状态：**使用中** / **已关机** / **已删除**
- SSH 配置：端口、用户名、密码（详情页编辑，留空不修改）

### 3. 主机密钥管理

- 统一管理 SSH 密钥凭据，支持多台主机复用同一密钥
- **密码认证**：保存 SSH 密码，适合公司统一密码场景
- **私钥认证**：粘贴 RSA / Ed25519 私钥内容，支持私钥密码保护
- 每个密钥可设置用户名、端口、备注
- **默认密钥**：设为默认后 SSH 连接自动优先使用
- 密钥列表不显示敏感字段原文，编辑时才展示

### 4. SSH Web 终端（增强版）

基于 **xterm.js + paramiko + WebSocket** 的全功能网页 SSH 终端：

**工具栏：**
- 复制 / 粘贴（选中文字自动复制到剪贴板）
- 清屏、字体缩放（10~24px）、全屏模式
- 断开连接 / 重新连接

**终端特性：**
- Tokyo Night 暗色主题
- 连接状态实时指示（绿色圆点 + 连接时长计时）
- 底部状态栏：主机 IP、用户名、终端尺寸、已连接时长
- 登录时可选择认证方式：资产自带凭据 / 已保存的 SSH 密钥
- 有默认密钥时自动选中

**文件管理器（SFTP）：**
- 右侧面板，点击工具栏文件夹图标打开
- 目录浏览：文件名、大小、修改时间、权限
- 路径导航栏 + 快捷路径（/、~、/tmp、/etc、/var/log）
- **上传文件**：选择本地文件上传到当前目录
- **下载文件**：右键菜单直接下载到本地
- **在线编辑**：双击文本文件打开编辑器，修改后直接保存
- **新建目录** / **重命名** / **删除**（右键菜单操作）

**部署方式：** xterm.js + paramiko + WebSocket，WebSocket 端点：`/api/v1/ws/ssh/{asset_id}`

### 5. 容器管理（K8s 自动发现）

- 对接 **Kubernetes API**，输入 API Server 地址 + ServiceAccount Token 即可接入集群
- **连接测试**：接入前自动测试 K8s API 连通性，显示集群版本
- **Token 过期检测**：集群状态为 stopped 时，悬停显示具体原因（Token 过期 / 连接超时 / 权限不足）
- **集群编辑**：支持编辑集群信息和更新 Token，无需删除重建
- **资源自动发现**：实时从 K8s API 拉取所有资源，无需手动录入
- **集群概览**：节点数、就绪节点、Pods、Deployments、Services、命名空间统计
- **节点管理**：节点名称、状态（Ready/NotReady）、IP、CPU、内存、kubelet 版本、系统、容器运行时
- **Pod 管理**：按命名空间筛选、关键词搜索，显示状态、节点、IP、镜像、重启次数；支持分页（10/20/50/100 条/页），搜索和筛选时自动重置页码
- **Deployment 管理**：副本状态（ready/total）、镜像、命名空间筛选；支持分页
- **Service 管理**：类型（ClusterIP/NodePort/LoadBalancer）、Cluster IP、端口、Selector；支持分页
- **命名空间 / 节点**：概览表格均支持分页（10/20/50 条/页）

### 6. Docker 监控（Agent 拉取模式）

- 采用 **Portainer 风格**：目标主机部署轻量 Agent 容器，平台主动拉取数据
- **一键部署**：注册主机时直接显示 `docker run` 命令，复制即可
- **自动发现**：Agent 每 5 秒采集容器数据，平台每 10 秒自动拉取
- **主机管理**：注册、编辑、删除 Docker 主机，自动检测在线/离线状态
- **独立详情页**：点击主机进入独立详情页（路由 `/docker/:id`），展示主机信息、系统指标（CPU/内存/磁盘带进度条）、容器列表
- **容器列表**：容器名称、镜像、状态、端口映射，支持搜索和状态筛选
- **实时指标**：CPU%、内存使用（进度条+数值）、网络 I/O、磁盘 I/O、重启次数
- **系统指标**：主机 CPU/内存/磁盘使用率、Docker 版本、系统信息
- **手动刷新**：支持一键手动从 Agent 拉取最新数据

**Agent 部署：**

```bash
docker run -d -p 9001:9001 \
  --name ops-agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  hub1.lczy.com/public/ops-agent:latest
```

**Agent API：**

| 路径 | 说明 |
|------|------|
| `GET /ping` | 健康检查 |
| `GET /info` | 主机系统信息 |
| `GET /containers` | 容器列表及指标 |
| `GET /snapshot` | 一次性返回全部数据 |

### 7. 主机监控（Prometheus）

- 对接 **Prometheus + node_exporter**，实时采集主机指标
- 主机列表展示：CPU、内存、磁盘、网络、负载（颜色阈值：🟢→🟡→🔴）
- 单机详情：圆形进度条 + 磁盘读写、TCP 连接、进程数、运行时间等
- Prometheus 连接状态指示
- 批量并发查询，一次 HTTP 请求获取所有主机数据

**采集的核心指标：**

| 指标 | PromQL |
|------|--------|
| CPU 使用率 | `100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| 内存使用率 | `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` |
| 磁盘使用率 | `(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100` |
| 网络流量 | `rate(node_network_receive/transmit_bytes_total[5m]) * 8` |
| 系统负载 | `node_load1 / node_load5 / node_load15` |

### 8. 告警规则（Prometheus）

- 从 Prometheus `/api/v1/rules` 拉取告警规则
- 展示：规则名称、PromQL 表达式、严重程度、状态（inactive/pending/firing）、持续时间、健康状态
- 支持按 severity 和 state 筛选

### 9. 告警事件（Alertmanager Webhook）

- Alertmanager 通过 **webhook** 推送告警事件到后端，自动存入数据库
- 告警事件表格：ID、来源信息、告警名称、严重程度、状态、告警值、告警摘要、连续触发次数、触发时间、恢复时间
- 支持关键词搜索 + 严重程度/状态筛选
- 每行可展开查看原始 labels/annotations JSON
- 告警值自动从 description 中提取百分比数值

### 10. 告警管理

- 告警新增、编辑、删除（弹窗表单）
- 告警状态：待确认 → 已确认 → 已解决 / 已忽略
- 告警级别：低 / 中 / 高 / 严重

### 11. 工单协作

- 工单新增、编辑、删除（弹窗表单）
- 工单状态：待处理 → 处理中 → 已解决 → 已关闭
- 工单优先级：低 / 普通 / 高 / 紧急
- 支持关联资产

### 12. 批量执行

- 从资产列表中**勾选多台主机**，输入命令，并发执行
- 基于 **WebSocket + paramiko**，实时返回每台主机的输出
- 暗色终端风格输出面板，按主机分屏展示
- **执行历史**：记录每次执行的命令、主机、结果，支持搜索和删除
- WebSocket 端点：`/api/v1/batch-exec/ws/exec`

### 13. 巡检中心

- **一键巡检**：手动触发，自动检查主机、K8s 集群、资产状态
- **主机巡检**（Prometheus）：CPU、内存、磁盘、负载各项指标独立检查，阈值可自定义
- **K8s 巡检**：节点 NotReady、异常 Pod（Failed/Unknown）、Pending Pod、频繁重启 Pod（>5次）
- **资产巡检**：已关机资产告警
- **巡检报告**：按严重程度分级（正常/警告/严重），按分类分组展示（主机/K8s/资产）
- **主机巡检卡片布局**：每台主机一行摘要（名称 + IP + 正常/警告/严重计数），点击可展开查看 CPU、内存、磁盘、负载详细指标；有异常的主机自动展开，正常主机默认折叠；异常主机优先排序
- **巡检阈值配置**：独立配置页面，2×2 卡片网格布局，每项指标支持滑块调节 + 三色预览条（绿/黄/红），提供「严格 / 标准 / 宽松」三档快捷预设，支持恢复默认
- 报告列表 + 详情弹窗 + **导出 Excel**（状态自动着色、中文分类、支持中文文件名）+ 删除

### 14. 报表中心

- **预置报表**：8 种内置报表（资产统计、工单统计、告警统计等）
- **自定义报表**：选择数据源 + 维度 + 时间范围
- **CSV 导出**：一键导出报表数据

### 15. 用户与权限

- 用户管理：CRUD + 分配角色
- 角色权限（RBAC）：三级权限树（页面 → 子页面 → 功能），支持批量全选/反选
- 页面级 + 接口级权限校验，侧边栏按权限动态显示

### 16. 审计日志

- 自动记录关键操作：增删改 + 登录登出 + SSH 连接 + SFTP 上传/下载/删除 + 配置变更 + 批量执行
- **真实客户端 IP 采集**：优先读取 `X-Forwarded-For` / `X-Real-IP`（反向代理场景），回退到直连 IP；开发环境下 Vite 代理自动透传客户端 IP
- 搜索栏：关键词 + 操作类型 + 对象类型 + 时间范围

### 17. 仪表盘（数据驱动风格）

- **问候语 + 日期**：根据时间段自动显示早上好/下午好/晚上好，当前日期
- **时间筛选**：今天 / 本周 / 本月（UI 展示）
- **4 张统计卡片**：资产总数 / 在线主机 / 待处理告警 / 待处理工单，每张卡片包含：
  - 图标 + 大号数值
  - SVG Sparkline 迷你趋势图（近 7 天数据）
  - 变化百分比（绿色上升 / 红色下降 / 灰色持平）
- **活动时间线**（左侧）：从审计日志实时拉取，支持分类筛选（全部 / 告警 / 工单 / 资产 / 巡检 / 用户），独立滚动区域，每类最多 10 条
- **图表区**（右侧）：
  - 告警趋势面积图（近 7 天 SVG 面积图 + 数据点）
  - 资产类型分布（横向条形图 + 百分比）
- **响应式布局**：600px / 1100px / 1600px / 1920px 四档断点
- 所有图表纯 SVG 实现，无第三方图表库依赖

### 18. 配置中心

- 通过 UI 管理 Prometheus / Alertmanager 服务地址，无需改代码重启
- **连接测试**：一键测试 Prometheus / Alertmanager 是否可达
- DB 优先读取，fallback 到 `config.py` 常量，无缝升级
- 配置变更自动写入审计日志

---

## UI 设计

- 深色海军蓝侧边栏 + 白色内容区，蓝色主色调（#3b82f6）
- 登录页：暗色渐变背景 + 玻璃拟态卡片 + 浮动几何装饰动画
- SSH 终端：Tokyo Night 暗色主题，工具栏 + 文件管理器
- 弹窗表单、圆形进度条、药丸形状态标签、迷你进度条
- 响应式：1100px / 860px / 600px 三档断点
- **图标按需加载**：只打包实际使用的 Element Plus 图标（26 个 vs 300+），减小打包体积

---

## 默认登录账号

- 账号：`admin`
- 密码：`admin123`

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia + Vite 8 |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 数据库 | MySQL 8 |
| 监控 | Prometheus + node_exporter |
| 告警 | Alertmanager (webhook) |
| 容器 | Kubernetes API（httpx 直连） |
| Docker | Agent（HTTP 拉取模式） |
| 部署 | Docker Compose（一键部署 MySQL + 后端 + 前端） |
| SSH | xterm.js + paramiko + WebSocket（终端 + SFTP 文件管理） |
| 认证 | JWT (pbkdf2_sha256) + 图形验证码 (captcha) |

---

## 项目结构

```
my-project/
├── backend/
│   └── app/
│       ├── api/                # REST API
│       │   ├── auth.py         # 认证
│       │   ├── assets.py       # 资产管理
│       │   ├── ssh.py          # SSH WebSocket + SFTP 文件管理
│       │   ├── ssh_keys.py     # SSH 密钥管理
│       │   ├── monitoring.py   # 主机监控（Prometheus）
│       │   ├── alertmanager.py # Alertmanager（告警规则/事件/Webhook）
│       │   ├── alerts.py       # 告警管理
│       │   ├── tickets.py      # 工单
│       │   ├── containers.py   # 容器（K8s API 自动发现）
│       │   ├── docker_mgmt.py  # Docker 监控（主机管理 + 容器查询）
│       │   ├── batch_exec.py   # 批量执行（WebSocket）
│       │   ├── patrol.py       # 巡检中心
│       │   ├── settings.py     # 配置中心
│       │   ├── reports.py      # 报表
│       │   ├── dashboard.py    # 仪表盘
│       │   ├── users.py        # 用户
│       │   ├── roles.py        # 角色权限
│       │   ├── audit.py        # 审计
│       │   └── password.py     # 密码
│       ├── core/               # 配置 + JWT + settings
│       ├── db/                 # 数据库连接与初始化
│       ├── models/             # SQLAlchemy 模型
│       │   ├── alert.py        # 告警
│       │   ├── alert_event.py  # 告警事件
│       │   ├── asset.py        # 资产
│       │   ├── audit.py        # 审计
│       │   ├── batch_exec.py   # 批量执行记录
│       │   ├── container.py    # 容器（集群/Pod/Service/Deployment）
│       │   ├── patrol.py       # 巡检报告 + 巡检项
│       │   ├── rbac.py         # 角色权限
│       │   ├── ssh_key.py      # SSH 密钥
│       │   ├── system_config.py # 系统配置
│       │   ├── ticket.py       # 工单
│       │   └── user.py         # 用户
│       └── services/           # 业务逻辑层
│           ├── prometheus.py   # Prometheus 查询服务
│           ├── alertmanager.py # Alertmanager 查询 + Webhook 处理
│           ├── k8s.py          # Kubernetes API 客户端
│           ├── docker_agent.py # Docker Agent 服务层
│           ├── containers.py   # 容器数据服务
│           ├── captcha.py      # 图形验证码生成与校验
│           ├── batch_exec.py   # 批量 SSH 执行服务
│           └── patrol.py       # 巡检执行服务
├── frontend/
│   └── src/
│       ├── api/                # API 请求层
│       │   ├── request.ts      # Axios 封装
│       │   ├── sshKeys.ts      # SSH 密钥 API
│       │   └── sftp.ts         # SFTP 文件管理 API
│       ├── components/         # 通用组件（Sparkline、AlertTrendChart 等）
│       ├── layouts/            # 布局组件
│       ├── router/             # 路由 + 守卫
│       ├── stores/             # Pinia 状态管理
│       ├── utils/
│       │   └── icons.ts        # Element Plus 图标按需注册
│       └── views/
│           ├── login/          # 登录页（玻璃拟态）
│           ├── dashboard/      # 仪表盘（数据驱动风格）
│           ├── assets/         # 资产管理 + 主机密钥
│           ├── monitoring/     # 监控告警 + SSH 终端（含 SFTP）
│           ├── containers/     # 容器（集群列表 + 资源详情 + Docker 监控 + 主机详情）
│           ├── batch/          # 批量执行
│           ├── patrol/         # 巡检中心
│           ├── tickets/        # 工单
│           ├── reports/        # 报表
│           ├── settings/       # 配置中心
│           ├── users/          # 用户
│           ├── roles/          # 角色
│           ├── audit/          # 审计
│           └── password/       # 密码
├── agent/                    # Docker 容器监控 Agent
│   ├── docker_agent.py       # Agent 主程序（HTTP 服务器）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── docker/                   # Docker 部署
│   ├── docker-compose.yml    # 一键部署编排
│   ├── .env.example          # 环境变量模板
│   └── nginx.conf            # nginx 配置（SPA + API 反代）
├── .dockerignore
└── README.md
```

---

## Docker Compose 部署（推荐）

一键启动整个项目：MySQL + 后端 + 前端 + 可选 Agent。

```bash
cd docker
cp .env.example .env
# 按需修改 .env 中的密码和端口
docker compose up -d
```

访问 `http://服务器IP`（默认 80 端口，可通过 `FRONTEND_PORT` 自定义）。

**自定义端口：**

```bash
# .env 中修改
FRONTEND_PORT=3000

# 或命令行指定
FRONTEND_PORT=3000 docker compose up -d
```

**启动 Agent（可选）：**

```bash
docker compose --profile agent up -d
```

**服务架构：**

| 服务 | 容器名 | 默认端口 | 说明 |
|------|--------|---------|------|
| mysql | ops-mysql | 3306 | MySQL 8.0，数据持久化到 volume |
| backend | ops-backend | 8000 | FastAPI，等 mysql 健康后启动 |
| frontend | ops-frontend | 80（可自定义） | nginx 托管 SPA + 反代 API |
| agent | ops-agent | 9001 | 可选，需 `--profile agent` 启动 |

**常用命令：**

```bash
cd docker
docker compose up -d              # 启动
docker compose down               # 停止
docker compose logs -f backend    # 查看后端日志
docker compose up -d --build      # 重新构建镜像
docker compose ps                 # 查看运行状态
```

---

## 本地开发启动

### 后端

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npx vite --host
```

- 前端 SPA：`http://localhost:3000`
- 后端 API：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

数据库：MySQL `ops_platform`（启动时自动建库建表，含自动迁移）

默认连接：`localhost:3306`，`root` / `123456`

后端 MySQL 配置支持环境变量覆盖，兼容本地开发和容器部署：

```bash
# 可通过环境变量覆盖默认值
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=123456
export MYSQL_DATABASE=ops_platform
```

---

## 依赖服务

| 服务 | 用途 | 配置位置 |
|------|------|---------|
| MySQL | 数据存储 | `backend/app/core/config.py` |
| Prometheus | 主机指标采集 | 配置中心 UI 或 `config.py` → `PROMETHEUS_URL` |
| Alertmanager | 告警推送 | 配置中心 UI 或 `config.py` → `ALERTMANAGER_URL` |
| Kubernetes | 容器资源发现 | 集群接入时填写 API Server + Token |
| Docker Agent | Docker 容器监控 | 目标主机部署 Agent 容器，平台注册时填写 IP:端口 |
| node_exporter | 主机指标暴露 | 每台主机部署，端口 9100 |

> **提示：** Prometheus 和 Alertmanager 的地址可以在系统管理 → 配置中心中通过 UI 修改，无需改代码重启。

### Prometheus 部署参考

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['host1:9100', 'host2:9100']

rule_files:
  - 'alerts/*.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Alertmanager 部署参考

```yaml
# alertmanager.yml
route:
  receiver: 'ops-platform'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'ops-platform'
    webhook_configs:
      - url: 'http://<backend>:<port>/api/v1/alertmanager/webhook'
        send_resolved: true
```

### Kubernetes 接入参考

容器管理模块通过 K8s API 自动发现集群资源，需要提供 API Server 地址和 ServiceAccount Token。

**获取 Token：**

```bash
# 创建长期 Token（有效期 10 年）
kubectl create token default --duration=87600h

# 或创建专用 ServiceAccount
kubectl create serviceaccount ops-monitor -n kube-system
kubectl create clusterrolebinding ops-monitor --clusterrole=view --serviceaccount=kube-system:ops-monitor
kubectl create token ops-monitor -n kube-system --duration=87600h
```

> 建议使用 `view` 角色的 ServiceAccount，只读权限即可。

### Docker Agent 接入参考

Docker 监控通过在目标主机部署轻量 Agent 容器实现，Agent 暴露 HTTP API 供平台拉取数据。

**部署 Agent：**

```bash
docker run -d -p 9001:9001 \
  --name ops-agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  hub1.lczy.com/public/ops-agent:latest
```

**构建镜像：**

```bash
cd agent
docker build -t hub1.lczy.com/public/ops-agent:latest .
docker push hub1.lczy.com/public/ops-agent:latest
```

**平台注册：**

进入 资产管理 → Docker 监控 → 注册主机，填写名称和 Agent 地址（`目标IP:9001`）即可。平台每 10 秒自动从 Agent 拉取数据。

---

## REST API（v1）

所有 API 以 `/api/v1` 为前缀，统一返回格式：

```json
{ "code": 0, "msg": "ok", "data": { ... } }
```

认证方式：`Authorization: Bearer <token>`（JWT）

### 主要端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /auth/login` | 登录（需验证码） |
| 认证 | `GET /auth/captcha` | 获取图形验证码 |
| 资产 | `GET/POST/PUT/DELETE /assets/` | 资产 CRUD |
| SSH 密钥 | `GET/POST/PUT/DELETE /ssh-keys/` | SSH 密钥 CRUD |
| SSH 终端 | `WS /ws/ssh/{asset_id}` | SSH 终端（WebSocket） |
| SFTP | `GET /ssh/{id}/sftp/list` | 列出目录内容 |
| SFTP | `GET /ssh/{id}/sftp/read` | 读取文件内容 |
| SFTP | `POST /ssh/{id}/sftp/write` | 写入文件 |
| SFTP | `POST /ssh/{id}/sftp/upload` | 上传文件 |
| SFTP | `GET /ssh/{id}/sftp/download` | 下载文件 |
| SFTP | `POST /ssh/{id}/sftp/mkdir` | 创建目录 |
| SFTP | `POST /ssh/{id}/sftp/remove` | 删除文件/目录 |
| SFTP | `POST /ssh/{id}/sftp/rename` | 重命名 |
| 监控 | `GET /monitoring/hosts` | 主机监控列表（Prometheus） |
| 监控 | `GET /monitoring/hosts/{id}` | 主机详情 |
| 告警规则 | `GET /alertmanager/rules` | Prometheus 告警规则 |
| 告警事件 | `GET /alertmanager/events` | 告警事件历史 |
| 告警管理 | `GET/POST/PUT/DELETE /alerts/` | 告警 CRUD |
| Webhook | `POST /alertmanager/webhook` | Alertmanager 推送 |
| 工单 | `GET/POST/PUT/DELETE /tickets/` | 工单 CRUD |
| 容器 | `GET/POST/PUT/DELETE /containers/clusters` | 集群管理 |
| 容器 | `POST /containers/test-connection` | 测试 K8s 连接 |
| 容器 | `GET /containers/clusters/{id}/resources` | 集群全部资源（实时） |
| 容器 | `GET /containers/clusters/{id}/nodes` | 节点列表 |
| 容器 | `GET /containers/clusters/{id}/pods` | Pod 列表 |
| 容器 | `GET /containers/clusters/{id}/services` | Service 列表 |
| 容器 | `GET /containers/clusters/{id}/deployments` | Deployment 列表 |
| Docker | `GET /containers/docker/overview` | Docker 监控概览 |
| Docker | `GET/POST/PUT/DELETE /containers/docker/hosts` | Docker 主机 CRUD |
| Docker | `POST /containers/docker/hosts/{id}/refresh` | 手动刷新（从 Agent 拉取） |
| Docker | `GET /containers/docker/containers` | Docker 容器列表 |
| Docker | `GET /containers/docker/hosts/{id}/containers` | 指定主机容器列表 |
| 批量执行 | `WS /batch-exec/ws/exec` | 批量命令执行（WebSocket） |
| 批量执行 | `GET /batch-exec/history` | 执行历史 |
| 巡检 | `POST /patrol/run` | 手动触发巡检 |
| 巡检 | `GET /patrol/reports` | 巡检报告列表 |
| 巡检 | `GET /patrol/reports/{id}` | 巡检报告详情 |
| 巡检 | `GET /patrol/reports/{id}/export` | 导出巡检报告 Excel |
| 巡检 | `GET /patrol/thresholds` | 获取巡检阈值配置 |
| 巡检 | `PUT /patrol/thresholds` | 批量更新巡检阈值 |
| 巡检 | `PUT /patrol/thresholds/{key}` | 更新单个巡检阈值 |
| 配置 | `GET/PUT /settings/` | 系统配置 |
| 配置 | `POST /settings/test-connection/{service}` | 测试 Prometheus/Alertmanager |
| 报表 | `GET/POST /reports/` | 报表管理 |
| 用户 | `GET/POST/PUT/DELETE /users/` | 用户 CRUD |
| 角色 | `GET/POST/PUT/DELETE /roles/` | 角色 CRUD |
| 仪表盘 | `GET /dashboard/stats` | 仪表盘统计数据 |
| 仪表盘 | `GET /dashboard/summary` | 仪表盘汇总数据 |
| 仪表盘 | `GET /dashboard/sparkline` | 近 7 天趋势数据 |
| 仪表盘 | `GET /dashboard/activities` | 活动时间线（审计日志） |
| 仪表盘 | `GET /dashboard/alert-trend` | 近 7 天告警趋势 |
| 审计 | `GET /audit/` | 审计日志 |

详见 Swagger 文档：`http://localhost:8000/docs`
