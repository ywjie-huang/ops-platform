# 应用发布模块 — 使用文档

## 目录

- [概述](#概述)
- [核心概念](#核心概念)
- [快速开始](#快速开始)
- [功能详解](#功能详解)
  - [应用管理](#1-应用管理)
  - [环境管理](#2-环境管理)
  - [环境配置（应用×环境）](#3-环境配置应用环境)
  - [部署执行](#4-部署执行)
  - [部署记录与日志](#5-部署记录与日志)
  - [回滚](#6-回滚)
  - [审批流程](#7-审批流程)
  - [配置管理](#8-配置管理)
  - [文件上传](#9-文件上传)
- [部署策略](#部署策略)
  - [SSH 部署](#ssh-部署)
  - [Docker 部署](#docker-部署)
  - [Kubernetes 部署](#kubernetes-部署)
- [构建模式](#构建模式)
  - [本地构建](#本地构建)
  - [Jenkins 构建](#jenkins-构建)
- [权限说明](#权限说明)
- [数据库表结构](#数据库表结构)
- [API 接口一览](#api-接口一览)
- [常见问题](#常见问题)

---

## 概述

应用发布模块提供从代码构建到部署上线的完整自动化能力，支持三种部署策略（SSH / Docker / Kubernetes）、两种构建方式（本地构建 / Jenkins）、可选审批流程、一键回滚，以及部署日志实时推送。

**核心能力：**

- 📦 **应用管理**：维护应用基本信息、Git 仓库、构建配置
- 🌍 **多环境部署**：一套应用可配置 dev / staging / prod 等多套环境，每套环境独立配置部署目标
- 🚀 **三种部署策略**：SSH 文件上传 + 脚本执行、Docker 容器编排、Kubernetes Deployment 滚动更新
- 🔨 **灵活构建**：支持本地 SSH 构建和 Jenkins CI 触发
- ✅ **审批流程**：生产环境可开启部署审批，审批通过后自动执行
- ⏪ **一键回滚**：基于部署配置快照，快速回退到历史版本
- 📊 **实时日志**：SSE 推送部署过程日志，终端风格展示
- 🔐 **配置管理**：环境变量/配置项集中管理，敏感字段加密存储

---

## 核心概念

### 数据模型关系

```
DeployApplication（应用）
    ├── DeployAppEnv（应用×环境配置）──→ DeployEnvironment（环境）
    ├── DeployRecord（部署记录）
    ├── DeployConfig（配置项）──→ DeployEnvironment（环境，可选）
    └── DeployApproval（审批记录，关联 Record）
```

| 概念 | 说明 |
|------|------|
| **应用 (Application)** | 一个可部署的单元，包含名称、类型、Git 信息、构建配置 |
| **环境 (Environment)** | 部署目标环境，如 dev / staging / prod，系统预置三个环境 |
| **环境配置 (AppEnv)** | 应用在某个环境下的具体部署配置（目标主机、镜像、脚本等），是部署执行的核心输入 |
| **部署记录 (Record)** | 每次部署执行的完整记录，包含状态、日志、耗时、配置快照 |
| **审批 (Approval)** | 关联部署记录，需要审批人通过或拒绝后才可执行部署 |
| **配置项 (Config)** | 应用的键值对配置，支持按环境隔离，敏感字段加密存储 |

### 部署状态流转

```
pending → building → deploying → success
                     → failed
           → failed
  → cancelled
```

| 状态 | 说明 |
|------|------|
| `pending` | 已创建，等待执行（可能在等待审批） |
| `building` | 正在构建（本地编译或 Jenkins 构建中） |
| `deploying` | 构建完成，正在执行部署策略 |
| `success` | 部署成功 |
| `failed` | 部署失败（构建失败、脚本执行失败、健康检查超时等） |
| `cancelled` | 已取消（手动取消或审批拒绝） |

---

## 快速开始

### 第一步：创建应用

1. 进入 **应用发布 → 应用管理**，点击 **创建应用**
2. 填写基本信息：
   - **应用名称**：唯一标识，如 `my-web-app`
   - **应用类型**：web / api / worker / frontend / other
   - **部署策略**：选择 SSH / Docker / K8s（决定后续环境配置字段）
3. 填写 Git 信息（可选）：
   - **Git 仓库地址**：如 `https://github.com/org/repo.git`
   - **分支**：默认 `main`
4. 填写构建配置：
   - **构建方式**：本地构建 或 Jenkins
   - **构建命令**（本地构建时）：如 `cd /opt/build && make build`
   - **产物路径**（本地构建时）：如 `/opt/build/dist/app.tar.gz`
   - **Jenkins Job 名称**（Jenkins 构建时）：如 `my-app-build`
5. 配置健康检查（可选）：
   - **健康检查 URL**：如 `http://localhost:8080/health`
   - **超时时间**：默认 30 秒

### 第二步：配置环境部署目标

1. 进入应用详情页 → **环境配置** 标签
2. 点击环境卡片上的 **编辑** 按钮
3. 根据部署策略填写对应字段：

**SSH 策略：**
   - 目标主机（从资产列表选择）
   - 部署路径（如 `/opt/apps/my-web-app`）
   - 部署脚本（如 `./deploy.sh`）

**Docker 策略：**
   - Docker 主机（从集群列表选择）
   - 镜像名称（如 `nginx:latest`）
   - 容器名称、端口映射、环境变量、网络等

**K8s 策略：**
   - K8s 集群（从集群列表选择）
   - 命名空间、Deployment 名称、容器名称
   - 镜像名称

### 第三步：执行部署

1. 在环境卡片上点击 **部署** 按钮
2. 填写版本号（commit hash、tag 等，可选）
3. 确认后开始执行
4. 自动跳转到部署详情页，实时查看日志

---

## 功能详解

### 1. 应用管理

**页面路径：** `/deploy/apps`

**功能：**
- 应用列表：卡片网格展示，支持按名称搜索、类型/策略/状态筛选
- 创建应用：表单填写所有配置项
- 编辑应用：修改已有应用配置
- 删除应用：级联删除所有关联的环境配置、部署记录、配置项
- 应用详情：查看完整信息和关联数据

**应用类型：**

| 类型 | 说明 |
|------|------|
| `web` | Web 前端应用 |
| `api` | 后端 API 服务 |
| `worker` | 后台任务/Worker 进程 |
| `frontend` | 纯前端静态资源 |
| `other` | 其他类型 |

**部署策略：**

| 策略 | 说明 |
|------|------|
| `ssh` | SSH 上传产物 + 执行脚本 |
| `docker` | SSH 到 Docker 主机执行 docker 命令 |
| `k8s` | 调用 K8s API 更新 Deployment 镜像 |

### 2. 环境管理

系统预置三个环境（首次启动后端时自动创建）：

| 环境 | 审批要求 | 说明 |
|------|---------|------|
| `dev` | 否 | 开发环境 |
| `staging` | 否 | 预发布/测试环境 |
| `prod` | 是 | 生产环境，部署前需要审批 |

环境可通过 API 管理（当前暂无独立 UI 页面）。

### 3. 环境配置（应用×环境）

**页面路径：** 应用详情页 → 环境配置标签

每个应用在每个环境下有独立的部署配置。这是部署执行时的核心输入。

**SSH 策略字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| 目标主机 | ✅ | 从资产列表选择，使用资产的 SSH 凭据 |
| 部署路径 | 否 | 远程目录，默认 `/opt/apps/{应用名}` |
| 部署脚本 | 否 | 部署后执行的脚本，如 `./deploy.sh` |

**Docker 策略字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| Docker 主机 | ✅ | 从集群列表选择（类型=Docker） |
| 镜像名称 | ✅ | 如 `nginx:latest`、`my-app:v1.2.3` |
| 容器名称 | 否 | 默认使用应用名 |
| 端口映射 | 否 | 如 `8080:80,443:443` |
| 环境变量 | 否 | JSON 格式 `{"KEY":"value"}` 或每行 `KEY=value` |
| 网络 | 否 | Docker 网络名 |
| 额外参数 | 否 | 追加到 `docker run` 的参数 |

**K8s 策略字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| K8s 集群 | ✅ | 从集群列表选择（类型=K8s） |
| 命名空间 | 否 | 默认 `default` |
| Deployment 名称 | ✅ | K8s Deployment 资源名 |
| 容器名称 | 否 | 默认取 Deployment 中第一个容器 |
| 镜像名称 | ✅ | 更新后的容器镜像 |

### 4. 部署执行

**触发方式：**
1. **手动部署**：在应用详情页的环境卡片上点击「部署」按钮
2. **回滚部署**：在部署详情页点击「回滚」按钮
3. **API 触发**：调用 `POST /api/v1/deploy/execute`

**执行流程：**

```
创建部署记录（status=pending）
    │
    ├── 需要审批？ ──→ 创建审批记录，等待审批
    │                     ├── 通过 → 继续执行
    │                     └── 拒绝 → status=cancelled
    │
    ├── 有构建配置？ ──→ status=building
    │                     ├── 本地构建：SSH 到构建主机执行命令
    │                     └── Jenkins：触发 Job → 等待队列 → 轮询状态
    │
    ├── status=deploying ──→ 执行部署策略
    │                     ├── SSH：SFTP 上传 → 执行脚本 → 健康检查
    │                     ├── Docker：pull → stop → rm → run → 健康检查
    │                     └── K8s：PATCH Deployment → 轮询 rollout → 健康检查
    │
    └── status=success / failed
```

**部署配置快照：** 每次执行时，会将当前的应用配置、环境配置、构建配置冻结为 JSON 快照存入 `deploy_config` 字段。回滚时使用此快照，确保配置一致性。

### 5. 部署记录与日志

**页面路径：** `/deploy/records`

**功能：**
- 全局记录列表：按应用/环境/状态筛选，分页浏览
- 部署详情：点击记录进入详情页

**部署详情页包含：**
- 状态进度条：直观展示 pending → building → deploying → success 流程
- 实时日志：终端风格（深色背景），通过 SSE 实时推送，自动滚动
- 元信息面板：应用名称、环境、触发方式、耗时、版本号
- 操作按钮：取消（执行中）、回滚（已完成）

**SSE 日志推送：**
- 前端通过 `GET /api/v1/deploy/records/{id}/log` 建立 SSE 连接
- 后端每秒轮询日志内容，增量推送给前端
- 部署完成后自动关闭连接

### 6. 回滚

**触发条件：** 部署记录状态为 `success`、`failed` 或 `cancelled` 时可回滚

**回滚流程：**
1. 点击部署详情页的「回滚」按钮
2. 系统基于原记录的 `deploy_config` 快照创建新记录
3. 新记录的 `trigger_type=rollback`，`rollback_from=原记录ID`
4. 自动跳转到新记录详情页，开始执行

**注意：** 回滚本质上是用旧配置重新执行一次部署，并非撤销操作。如果原部署涉及数据库迁移等不可逆操作，回滚无法恢复数据状态。

### 7. 审批流程

**页面路径：** `/deploy/approvals`

**工作原理：**
- 当目标环境的 `approval_required=True`（如 prod）时，部署不会立即执行
- 系统自动创建一条审批记录（status=pending）
- 审批人在审批页面查看部署信息，选择通过或拒绝
- 通过后自动触发部署执行
- 拒绝后自动取消关联的部署记录

**审批操作：**
- **通过**：点击「通过」按钮，可选填写审批意见
- **拒绝**：点击「拒绝」按钮，填写拒绝原因

### 8. 配置管理

**页面路径：** 应用详情页 → 配置管理标签

**功能：**
- 集中管理应用的环境变量/配置项
- 支持按环境隔离（同一 key 在不同环境可有不同 value）
- 敏感字段（密码、Token）加密存储，列表展示时显示 `******`

**字段说明：**

| 字段 | 说明 |
|------|------|
| Key | 配置项名称，如 `DB_PASSWORD` |
| Value | 配置值 |
| 环境 | 可选，为空表示全局配置 |
| 加密 | 勾选后，列表和 API 返回时显示 `******`，编辑时不会覆盖原值 |
| 描述 | 配置项说明 |

### 9. 文件上传

**页面路径：** `/deploy/upload`

这是独立于应用发布流程的 SFTP 文件上传功能，用于手动将文件上传到目标主机。

**使用方式：**
1. 选择目标主机（从资产列表）
2. 指定远程路径
3. 拖拽或选择文件上传

---

## 部署策略

### SSH 部署

**适用场景：** 传统服务器部署，需要上传构建产物并执行部署脚本。

**执行流程：**
1. 使用资产的 SSH 凭据（密码或密钥）连接目标主机
2. 创建部署目录（`mkdir -p`）
3. SFTP 上传构建产物（进度每 10% 输出一次日志）
4. SSH 执行部署脚本（`cd {部署路径} && {部署脚本}`，超时 300 秒）
5. 健康检查（HTTP GET，轮询直到成功或超时）

**前提条件：**
- 目标主机已在资产管理系统中添加
- 资产配置了 SSH 凭据（密码或密钥）
- 部署路径对 SSH 用户有写权限

### Docker 部署

**适用场景：** 容器化应用部署，通过 SSH 远程操作 Docker。

**执行流程：**
1. 从 Docker 集群配置中解析主机 IP
2. 查找对应资产获取 SSH 凭据
3. SSH 连接 Docker 主机
4. `docker pull {镜像}` — 拉取最新镜像（超时 300 秒）
5. `docker stop {容器名}` — 停止旧容器（忽略不存在的错误）
6. `docker rm {容器名}` — 删除旧容器
7. `docker run -d --name {容器名} --restart unless-stopped {端口} {环境变量} {网络} {额外参数} {镜像}` — 启动新容器
8. 健康检查

**前提条件：**
- Docker 主机已在集群管理中添加（类型=Docker）
- 主机 IP 对应的资产已添加到资产管理系统
- Docker 主机上已安装 Docker

### Kubernetes 部署

**适用场景：** K8s 集群中的应用镜像更新。

**执行流程：**
1. 读取 K8s 集群的 API Server 地址和 Token
2. `GET /apis/apps/v1/namespaces/{ns}/deployments/{name}` — 获取当前 Deployment
3. 构建 strategic-merge-patch，更新目标容器的镜像
4. `PATCH` Deployment — 触发滚动更新
5. 轮询 rollout 状态（每 5 秒，最多 180 秒）：
   - 检查 `Progressing=True` 且 `reason=NewReplicaSetAvailable`
   - 检查 `Available=True`
6. 健康检查

**前提条件：**
- K8s 集群已在集群管理中添加（类型=K8s）
- 集群配置了 API Server URL 和 ServiceAccount Token
- Token 有 PATCH Deployment 的权限

---

## 构建模式

### 本地构建

**适用场景：** 在构建服务器上手动编译，生成产物文件。

**流程：**
1. SSH 连接到构建主机
2. 执行构建命令（如 `cd /opt/build && make build`）
3. 检查产物文件是否存在
4. 将产物路径传递给部署策略

**配置项：**

| 字段 | 说明 | 示例 |
|------|------|------|
| 构建命令 | SSH 执行的构建脚本 | `cd /opt/project && npm run build` |
| 产物路径 | 构建产物的绝对路径 | `/opt/project/dist/app.tar.gz` |

### Jenkins 构建

**适用场景：** 使用 Jenkins CI/CD 流水线构建。

**流程：**
1. 通过 Jenkins REST API 触发指定 Job
2. 等待 Job 进入构建队列（最多 120 秒）
3. 轮询构建状态（最多 600 秒）
4. 构建成功后，从 Jenkins 获取产物路径
5. 将产物路径传递给部署策略

**Jenkins 全局配置（系统设置页面）：**

| 字段 | 说明 |
|------|------|
| URL | Jenkins 服务地址，如 `http://jenkins.example.com:8080` |
| 用户名 | Jenkins API 用户名 |
| Token | Jenkins API Token（在 Jenkins 个人设置中生成） |

**应用级配置：**

| 字段 | 说明 | 示例 |
|------|------|------|
| Jenkins Job 名称 | 要触发的 Job 名 | `my-app-build` |
| Jenkins Token | Job 的触发 Token（可选） | `build-token-123` |

---

## 权限说明

模块使用 RBAC 权限控制，共 8 个权限码：

| 权限码 | 说明 | 操作 |
|--------|------|------|
| `deploy.view` | 查看应用/记录 | 浏览应用列表、部署记录、查看详情 |
| `deploy.create` | 创建应用 | 新建应用 |
| `deploy.update` | 编辑应用 | 修改应用信息、环境配置 |
| `deploy.delete` | 删除应用 | 删除应用及其所有关联数据 |
| `deploy.execute` | 执行部署 | 触发部署执行、取消部署 |
| `deploy.approve` | 审批部署 | 通过/拒绝部署审批 |
| `deploy.rollback` | 回滚部署 | 执行回滚操作 |
| `deploy.config` | 管理配置 | 增删改查应用配置项 |

权限在数据库初始化时自动创建，默认 `admin` 角色拥有所有权限。

---

## 数据库表结构

### deploy_applications（应用表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| name | VARCHAR(100) | 应用名称（唯一） |
| description | TEXT | 描述 |
| app_type | VARCHAR(30) | 类型：web/api/worker/frontend/other |
| deploy_strategy | VARCHAR(20) | 策略：ssh/docker/k8s |
| status | VARCHAR(20) | 状态：active/archived |
| git_url | VARCHAR(500) | Git 仓库地址 |
| git_branch | VARCHAR(100) | 分支名 |
| build_mode | VARCHAR(20) | 构建方式：local/jenkins |
| build_command | TEXT | 本地构建命令 |
| artifact_path | VARCHAR(500) | 构建产物路径 |
| jenkins_job_name | VARCHAR(200) | Jenkins Job 名 |
| jenkins_token | VARCHAR(200) | Jenkins 触发 Token |
| health_check_url | VARCHAR(500) | 健康检查 URL |
| health_check_timeout | INT | 健康检查超时（秒） |
| creator_id | INT FK→users | 创建者 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### deploy_environments（环境表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| name | VARCHAR(50) | 环境名（唯一） |
| description | TEXT | 描述 |
| approval_required | BOOLEAN | 是否需要审批 |
| sort_order | INT | 排序权重 |
| created_at | DATETIME | 创建时间 |

### deploy_app_envs（应用×环境配置表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| app_id | INT FK→deploy_applications | 应用 ID |
| env_id | INT FK→deploy_environments | 环境 ID |
| enabled | BOOLEAN | 是否启用 |
| ssh_asset_id | INT FK→assets | SSH 目标主机 |
| deploy_path | VARCHAR(500) | 部署路径 |
| deploy_script | TEXT | 部署脚本 |
| docker_host_id | INT FK→container_clusters | Docker 主机 |
| docker_image | VARCHAR(500) | Docker 镜像 |
| docker_container_name | VARCHAR(200) | 容器名 |
| docker_ports | VARCHAR(500) | 端口映射 |
| docker_env_vars | TEXT | 环境变量 |
| docker_network | VARCHAR(100) | 网络 |
| docker_extra_args | TEXT | 额外参数 |
| k8s_cluster_id | INT FK→container_clusters | K8s 集群 |
| k8s_namespace | VARCHAR(100) | 命名空间 |
| k8s_deployment | VARCHAR(200) | Deployment 名 |
| k8s_container_name | VARCHAR(200) | 容器名 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### deploy_records（部署记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| app_id | INT FK→deploy_applications | 应用 ID |
| env_id | INT FK→deploy_environments | 环境 ID |
| app_env_id | INT FK→deploy_app_envs | 环境配置 ID |
| version | VARCHAR(100) | 版本号/commit/tag |
| status | VARCHAR(20) | 状态 |
| trigger_type | VARCHAR(20) | 触发方式：manual/rollback/webhook |
| trigger_user_id | INT FK→users | 触发人 |
| deploy_config | TEXT | 部署配置 JSON 快照 |
| log | TEXT | 执行日志 |
| error_message | TEXT | 错误信息 |
| duration | FLOAT | 耗时（秒） |
| rollback_from | INT | 回滚来源记录 ID |
| started_at | DATETIME | 开始时间 |
| finished_at | DATETIME | 结束时间 |
| created_at | DATETIME | 创建时间 |

### deploy_approvals（审批表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| record_id | INT FK→deploy_records | 关联部署记录 |
| status | VARCHAR(20) | 状态：pending/approved/rejected |
| approver_id | INT FK→users | 审批人 |
| comment | TEXT | 审批意见 |
| created_at | DATETIME | 创建时间 |
| resolved_at | DATETIME | 处理时间 |

### deploy_configs（配置表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| app_id | INT FK→deploy_applications | 应用 ID |
| env_id | INT FK→deploy_environments | 环境 ID（可选） |
| key | VARCHAR(200) | 配置键 |
| value | TEXT | 配置值 |
| is_encrypted | BOOLEAN | 是否加密 |
| description | TEXT | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## API 接口一览

所有接口前缀：`/api/v1`，需要 `Authorization: Bearer <JWT>` 请求头。

### 应用管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/deploy/apps` | deploy.view | 应用列表（支持 keyword/app_type/deploy_strategy/status 筛选） |
| GET | `/deploy/apps/{app_id}` | deploy.view | 应用详情 |
| POST | `/deploy/apps` | deploy.create | 创建应用 |
| PUT | `/deploy/apps/{app_id}` | deploy.update | 编辑应用 |
| DELETE | `/deploy/apps/{app_id}` | deploy.delete | 删除应用（级联删除） |

### 环境与环境配置

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/deploy/envs` | deploy.view | 环境列表 |
| GET | `/deploy/apps/{app_id}/envs` | deploy.view | 应用的环境配置列表 |
| PUT | `/deploy/apps/{app_id}/envs/{env_id}` | deploy.update | 创建/更新环境配置 |
| DELETE | `/deploy/apps/{app_id}/envs/{env_id}` | deploy.delete | 删除环境配置 |

### 部署执行

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/deploy/execute` | deploy.execute | 执行部署（需传 app_id, env_id, version） |
| POST | `/deploy/records/{id}/cancel` | deploy.execute | 取消正在执行的部署 |
| POST | `/deploy/records/{id}/rollback` | deploy.rollback | 回滚（创建新记录并执行） |

### 部署记录

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/deploy/records` | deploy.view | 记录列表（支持 app_id/env_id/status 筛选，分页） |
| GET | `/deploy/records/{id}` | deploy.view | 记录详情 |
| GET | `/deploy/records/{id}/log` | deploy.view | SSE 实时日志流 |

### 审批

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/deploy/approvals` | deploy.approve | 审批列表（支持 status 筛选） |
| POST | `/deploy/approvals/{id}/approve` | deploy.approve | 通过审批 |
| POST | `/deploy/approvals/{id}/reject` | deploy.approve | 拒绝审批（需传 comment） |

### 配置管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/deploy/apps/{app_id}/configs` | deploy.view | 配置列表（支持 env_id 筛选） |
| POST | `/deploy/apps/{app_id}/configs` | deploy.config | 新增配置 |
| PUT | `/deploy/configs/{id}` | deploy.config | 更新配置 |
| DELETE | `/deploy/configs/{id}` | deploy.config | 删除配置 |

---

## 常见问题

### Q: 部署时提示「未配置目标主机」？

检查应用详情页 → 环境配置 → 对应环境是否已选择目标主机/集群。

### Q: Docker 部署时提示「未找到 IP 为 x.x.x.x 的资产」？

Docker 策略需要通过主机 IP 查找资产以获取 SSH 凭据。请确保：
1. Docker 集群配置了正确的 `host_ip` 或 `endpoint`（格式 `IP:端口`）
2. 资产管理中存在该 IP 对应的资产
3. 资产配置了 SSH 凭据

### Q: Jenkins 构建一直超时？

- 检查 Jenkins 配置中的 URL、用户名、Token 是否正确
- 确认 Jenkins Job 名称拼写正确
- Job 触发 Token 需与 Jenkins 中配置的一致
- 网络需能从后端服务器访问 Jenkins

### Q: K8s 部署时提示「Deployment 不存在」？

- 确认命名空间和 Deployment 名称拼写正确
- 确认 K8s 集群的 Token 有读取 Deployment 的权限
- 可通过 `kubectl get deployment -n {namespace}` 验证

### Q: 生产环境部署没有触发审批？

检查 `deploy_environments` 表中 `prod` 环境的 `approval_required` 是否为 `true`。系统预置时默认开启。

### Q: 回滚后数据没有恢复？

回滚是用旧配置快照重新执行一次部署，只恢复应用配置和部署状态。如果涉及数据库迁移、数据写入等不可逆操作，需要手动处理数据回滚。

### Q: SSE 日志不推送？

- 检查浏览器是否支持 EventSource
- 检查是否有反向代理缓冲了 SSE 响应（需要关闭 proxy_buffering）
- 部署完成后 SSE 连接会自动关闭

### Q: 加密配置项编辑时怎么不覆盖原值？

编辑配置项时，加密字段的值会显示为 `******`。如果提交时值仍为 `******`，系统会自动跳过值的更新，只更新 key、描述等其他字段。只有输入新值时才会真正更新。
