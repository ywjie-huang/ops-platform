# 应用发布模块 — 功能文档

## 概述

应用发布模块是运维管理系统的核心功能之一，提供统一的应用部署管理能力。支持 **Jenkins 触发**、**SSH 文件上传部署**、**Docker 容器部署**（规划中）、**Kubernetes 部署**（规划中）四种方式。

核心价值：**发布状态集中管理 + 一键发布/回滚 + 发布历史可追溯**。

---

## 已完成功能 ✅

### 1. 应用管理

- 应用注册：名称、类型（后端/前端/服务/其他）、部署方式、仓库地址、分支
- 应用列表：关键词搜索、按部署方式/状态筛选、分页
- 应用详情：基本信息展示、环境配置管理、发布历史
- 应用编辑/删除（级联删除关联的环境配置和发布记录）

### 2. 环境管理

- 默认三个环境：开发环境（dev）、测试环境（staging）、生产环境（prod）
- 生产环境默认需要审批，开发/测试环境无需审批
- 支持自定义新增/编辑/删除环境

### 3. 应用×环境配置

每个应用在每个环境可以独立配置：

| 配置项 | 说明 |
|--------|------|
| Jenkins Job 名称 | Jenkins 构建任务名 |
| Jenkins 构建参数 | JSON 格式的默认参数 |
| SSH 目标主机 | 从资产列表中选择 |
| SSH 部署路径 | 文件上传的目标目录 |
| SSH 部署脚本 | 上传后执行的命令 |
| Docker 镜像 | 镜像地址（规划中） |
| K8s 集群/命名空间/Deployment | K8s 配置（规划中） |

### 4. 发布看板（首页）

- **应用×环境状态矩阵**：行=应用，列=环境，单元格=当前版本+状态
- 概览统计：应用总数、构建中数量、成功率、待审批数
- 快捷发布按钮（每行和右上角）
- 空状态引导

### 5. Jenkins 触发发布

- 填写版本号，平台调用 Jenkins API 触发构建
- 后台自动轮询 Jenkins 构建状态（构建中→成功/失败）
- 实时拉取 Jenkins 构建日志
- 支持构建参数传递

### 6. SSH 文件上传部署

- 支持拖拽或选择文件上传（jar、zip、tar.gz 等，最大 500MB）
- 通过 SFTP 上传到目标服务器的指定目录
- 自动执行配置的部署脚本
- 记录执行日志（上传结果 + 脚本输出）

### 7. 审批流程

- 生产环境发布自动进入待审批状态
- 具有 `deploy.approve` 权限的用户可以审批/驳回
- 审批通过后自动触发发布
- 审批记录可追溯

### 8. 发布历史与回滚

- 全局发布记录列表：按应用/环境/状态筛选
- 发布详情：概览信息 + 日志查看 + 审批记录
- 一键重试：失败/被驳回的发布可以重试
- 一键回滚：创建一条新发布记录，使用上一个成功版本

### 9. 权限控制

6 个权限码，集成到平台 RBAC 体系：

| 权限码 | 说明 |
|--------|------|
| `deploy.view` | 查看应用列表和发布记录 |
| `deploy.create` | 注册应用、创建环境 |
| `deploy.update` | 编辑应用配置、环境配置 |
| `deploy.execute` | 触发发布、重试、回滚 |
| `deploy.approve` | 审批/驳回发布 |
| `deploy.delete` | 删除应用和环境 |

超级管理员默认拥有全部权限。

---

## 使用指南

### 快速开始（5 分钟上手）

#### 第一步：注册应用

进入 **应用发布 → 应用管理** → 点"+ 注册应用"

- **应用标识**：填英文标识，如 `user-service`
- **显示名称**：填中文名，如 `用户服务`
- **部署方式**：选 `jenkins` 或 `ssh`

#### 第二步：配置环境

进入应用详情 → **环境配置** tab → 点"+ 添加环境配置"

**Jenkins 模式：**
- 选环境（dev/staging/prod）
- 填 Jenkins Job 名称
- 构建参数（可选，JSON 格式）

**SSH 模式：**
- 选环境
- 选目标主机（从资产列表）
- 填部署路径，如 `/opt/apps/user-service/`
- 填部署脚本，如 `bash deploy.sh`

#### 第三步：发布

**方式一：看板快捷发布**
- 发布看板 → 点"快捷发布"或每行的"发布"按钮

**方式二：应用详情发布**
- 应用详情 → 点右上角"发布"按钮

**方式三：发布记录页**
- 发布记录 → 可查看全局发布历史

### Jenkins 发布流程

```
选应用 → 选环境 → 填版本号 → 确认发布
   ↓
平台调用 Jenkins API 触发构建
   ↓
后台轮询 Jenkins 状态（每 10 秒）
   ↓
构建完成 → 更新状态为成功/失败
   ↓
可查看 Jenkins 构建日志
```

### SSH 部署流程

```
选应用 → 选环境 → 填版本号 → 拖入文件 → 上传并部署
   ↓
SFTP 上传文件到目标服务器
   ↓
SSH 执行部署脚本
   ↓
记录执行日志，更新状态
```

### 审批流程（生产环境）

```
开发者发起发布 → 状态变为"待审批"
   ↓
审批人在发布详情页审批/驳回
   ↓
审批通过 → 自动触发发布
驳回 → 状态变为"已驳回"，可重试
```

### 回滚流程

```
发布记录列表 → 找到目标记录 → 点"回滚"
   ↓
系统自动创建一条新发布记录
   ↓
使用上一个成功版本的配置重新发布
```

---

## 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/deploy/status` | 发布看板 | 首页，应用×环境状态矩阵 |
| `/deploy/apps` | 应用管理 | 应用列表，注册/编辑/删除 |
| `/deploy/apps/:id` | 应用详情 | 基本信息/环境配置/发布历史 |
| `/deploy/records` | 发布记录 | 全局发布历史 |
| `/deploy/records/:id` | 发布详情 | 概览/日志/审批 |

---

## API 端点

### 应用管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/deploy/apps` | 应用列表 |
| GET | `/api/v1/deploy/apps/{id}` | 应用详情 |
| POST | `/api/v1/deploy/apps` | 创建应用 |
| PUT | `/api/v1/deploy/apps/{id}` | 更新应用 |
| DELETE | `/api/v1/deploy/apps/{id}` | 删除应用 |

### 环境管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/deploy/envs` | 环境列表 |
| POST | `/api/v1/deploy/envs` | 创建环境 |
| PUT | `/api/v1/deploy/envs/{id}` | 更新环境 |
| DELETE | `/api/v1/deploy/envs/{id}` | 删除环境 |

### 环境配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/deploy/apps/{id}/envs` | 获取应用的环境配置 |
| POST | `/api/v1/deploy/apps/{id}/envs` | 保存环境配置 |
| DELETE | `/api/v1/deploy/apps/{id}/envs/{env_id}` | 移除环境配置 |

### 发布操作

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/deploy/records` | 发布记录列表 |
| GET | `/api/v1/deploy/records/{id}` | 发布详情 |
| POST | `/api/v1/deploy/records` | 触发发布（Jenkins/Docker/K8s） |
| POST | `/api/v1/deploy/records/upload` | 上传文件并部署（SSH） |
| POST | `/api/v1/deploy/records/{id}/retry` | 重试失败的发布 |
| POST | `/api/v1/deploy/records/{id}/rollback` | 回滚 |
| GET | `/api/v1/deploy/records/{id}/logs` | 获取发布日志 |

### 审批

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/deploy/pending` | 待审批列表 |
| POST | `/api/v1/deploy/records/{id}/approve` | 审批/驳回 |

### 看板

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/deploy/status` | 发布状态矩阵 |
| GET | `/api/v1/deploy/overview` | 概览统计 |

---

## 数据库表

| 表名 | 说明 |
|------|------|
| `deploy_applications` | 应用注册表 |
| `deploy_environments` | 环境定义表 |
| `deploy_app_envs` | 应用×环境配置表 |
| `deploy_records` | 发布记录表 |
| `deploy_approvals` | 审批记录表 |

---

## 文件清单

### 后端

| 文件 | 说明 |
|------|------|
| `backend/app/models/deploy.py` | 数据模型（5 张表） |
| `backend/app/api/deploy.py` | API 端点（20+ 个） |
| `backend/app/services/deploy/__init__.py` | 服务包 |
| `backend/app/services/deploy/apps.py` | 应用 CRUD |
| `backend/app/services/deploy/envs.py` | 环境 CRUD |
| `backend/app/services/deploy/records.py` | 发布记录、执行调度、回滚 |
| `backend/app/services/deploy/approvals.py` | 审批逻辑 |
| `backend/app/services/deploy/jenkins.py` | Jenkins REST API 客户端 |
| `backend/app/services/deploy/ssh_deployer.py` | SSH 部署服务 |

### 前端

| 文件 | 说明 |
|------|------|
| `frontend/src/api/deploy.ts` | API 函数 |
| `frontend/src/views/deploy/StatusView.vue` | 发布看板 |
| `frontend/src/views/deploy/AppListView.vue` | 应用管理 |
| `frontend/src/views/deploy/AppDetailView.vue` | 应用详情 |
| `frontend/src/views/deploy/DeployListView.vue` | 发布记录 |
| `frontend/src/views/deploy/DeployDetailView.vue` | 发布详情 |

---

## 待完成功能 🚧

### P1 — Docker 容器部署

- [ ] `services/deploy/docker_deployer.py` — Docker 部署服务
- [ ] 复用 `docker_agent.py` 基础设施
- [ ] 拉取新镜像 → 停旧容器 → 启动新容器
- [ ] 前端 Docker 镜像输入和容器状态展示

### P2 — Kubernetes 部署

- [ ] `services/deploy/k8s_deployer.py` — K8s 部署服务
- [ ] `services/k8s.py` 新增 `patch_deployment_image()` 函数
- [ ] 滚动更新 Deployment 镜像
- [ ] 前端 K8s 集群/命名空间选择器

### P3 — 增强功能

- [ ] **Webhook 触发**：提供回调 URL，Jenkins/GitHub 构建完成后自动通知平台更新状态
- [ ] **定时发布**：指定时间自动触发发布，复用 APScheduler
- [ ] **批量发布**：一次选择多个应用批量发布到同一环境
- [ ] **发布看板增强**：显示最近 N 天的发布趋势图
- [ ] **通知集成**：发布成功/失败后发送钉钉/飞书通知
- [ ] **Jenkins 配置页面**：在系统配置中添加 Jenkins 连接管理 UI
- [ ] **发布模板**：常用发布配置模板，一键复用
- [ ] **发布对比**：对比两个版本之间的差异
