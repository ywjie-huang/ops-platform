# my-project · 运维管理系统

基于 **Python + FastAPI + Jinja2 + MySQL** 的企业级运维后台管理系统，具备资产管理、容器管理、监控告警、报表分析、工单协作、审计日志、用户权限等核心能力。

---

## 导航结构

| 一级分组 | 二级菜单 | 说明 |
|---------|---------|------|
| **报表大屏** | 仪表盘 / 报表中心 | 系统概览 + 预置报表/自定义报表/CSV导出 |
| **资产管理** | 主机管理 / 容器管理 | 资产台账 + K8s/Docker 集群/Pod/Service |
| **监控告警** | 监控指标 / 主机监控 | 自定义指标 + 主机资源实时监控 |
| **用户管理** | 用户管理 / 角色权限 | RBAC 权限 + 菜单权限分配 |
| **系统管理** | 审计日志 | 操作审计 |
| 独立菜单 | 工单协作 / 告警中心 | 工单流转 + 告警处理 |

---

## 核心功能

### 1. 认证与账号

- 登录页（居中卡片式，蓝色 logo）
- 基于 MySQL 的用户表，`pbkdf2_sha256` 密码哈希
- 首次启动自动创建默认管理员
- 密码修改（含强度检测和一致性校验）

### 2. 主机管理（资产管理）

- 资产新增、编辑、删除（弹窗表单）
- 资产详情页（关联工单和告警）
- 资产状态、类型、负责人、说明等字段
- 搜索栏：关键词 + 类型筛选 + 状态筛选
- 表格支持列排序、前端分页

### 3. 容器管理

- **集群管理**：新增/编辑/删除 K8s 或 Docker 集群
- **Pod 管理**：按集群、状态筛选，显示命名空间、节点、IP、镜像、重启次数
- **Service 管理**：按集群筛选，显示类型、ClusterIP、端口、Selector
- 顶部指标卡：集群数 / Deployment / Pod / Service

### 4. 监控指标

- 12 个系统内置指标：CPU 利用率、内存使用率、磁盘使用率、磁盘读写速率、网络入出流量、TCP 连接数、系统负载、进程数等
- **支持自定义指标**：设置名称、编码、单位、分类、告警阈值、严重阈值
- 系统内置指标不可删除
- 按分类筛选、关键词搜索

### 5. 主机监控

- 基于资产管理的主机列表，表格形式展示
- 每台主机显示：CPU、内存、磁盘（进度条+数值）、网络、负载、负责人
- 颜色阈值：🟢 正常 → 🟡 告警 → 🔴 严重
- 点击「详情」进入单机详情页，圆形进度条展示 CPU/内存/磁盘/负载
- 详细数据：网络流量、磁盘 IO、进程统计、系统信息
- 数据来源：Linux 命令（top/df/free 等），当前为模拟数据

### 6. 工单协作

- 工单新增、编辑、删除（弹窗表单）
- 工单详情页（状态流转图）
- 工单状态：待处理 → 处理中 → 已解决 → 已关闭
- 工单优先级：低 / 普通 / 高 / 紧急
- 支持关联资产
- REST API：`GET/POST/PUT/DELETE /api/v1/tickets/`

### 7. 告警中心

- 告警新增、编辑、删除（弹窗表单）
- 告警详情页（状态流转图）
- 告警状态：待确认 → 已确认 → 已解决 / 已忽略
- 告警级别：低 / 中 / 高 / 严重
- REST API：`GET/POST/PUT/DELETE /api/v1/alerts/`

### 8. 报表中心

- **预置报表**：8 种内置报表（资产统计、工单统计、告警统计、用户活跃度等）
- **自定义报表**：选择数据源（资产/工单/告警/用户/审计）+ 维度 + 时间范围
- **CSV 导出**：一键导出报表数据
- **定时发送**：配置报表定时邮件推送（UI 框架就绪）

### 9. 用户管理

- 用户新增、编辑、删除（弹窗表单）
- 支持分配多个角色
- 当前登录用户不可删除自己

### 10. 角色权限管理（RBAC）

- 角色新增、修改（弹窗表单）
- **分配菜单**：树形弹窗，按「父页面 → 子页面 → 功能」三级结构勾选权限
  - 联动逻辑：勾选任意功能 → 子页面自动勾选 → 父页面自动勾选
  - 批量操作：全选/反选（按功能类型：查询 / 新增 / 修改 / 删除）
  - 超级管理员（admin）不允许调整权限，按钮置灰
- 系统内置角色保护
- 已分配用户的角色不可删除

### 11. 审计日志

- 自动记录关键操作：资产 / 用户 / 角色 / 工单 / 告警 / 容器 / 监控指标的增删改 + 登录登出
- 搜索栏：关键词 + 操作类型 + 对象类型 + 时间范围筛选
- 只读页面

### 12. 权限控制

- 页面级 + 接口级权限校验
- 按钮级可见性控制
- 侧边栏按权限动态显示菜单

### 13. 仪表盘

- 4 张指标卡片横排：资产总数 / 在线 / 离线 / 待处理工单
- 左右分栏：资产表格 + 类型分布 / 工单动态 + 告警动态 + 角色分布

---

## UI 设计

### 设计风格

- 企业级运维管理平台风格
- 深色海军蓝侧边栏 + 白色内容区
- 蓝色主色调（#3b82f6），克制、专业
- SVG 线条图标，统一视觉语言

### 侧边栏结构

- 品牌 logo + 用户卡片
- 一级分组可展开/折叠，二级菜单带独立图标
- 分组：数据（报表大屏）/ 资产（资产管理）/ 监控（监控告警）/ 业务（工单、告警）/ 用户（用户管理）/ 系统（系统管理）
- 底部：修改密码 + 退出登录

### 交互组件

- **弹窗（Modal）**：新增/编辑通过弹窗完成，ESC 或点击背景关闭
- **分配菜单弹窗**：三级树形表格 + 批量全选/反选操作
- **表格（TableKit）**：列排序 + 前端分页 + 每页条数切换
- **圆形进度条（Gauge）**：SVG 圆环动画，阈值变色
- **迷你进度条**：表格内药丸形进度条 + 数值
- **筛选栏**：SVG 搜索框 + 下拉筛选
- **状态标签**：药丸形彩色标签
- **详情页**：双栏信息卡 + 状态流转图

### 响应式

- 1100px 以下：两栏布局变单栏
- 860px 以下：侧边栏静态，内容区全宽
- 600px 以下：指标卡片、筛选栏变单列

---

## 默认登录账号

- 账号：`admin`
- 密码：`admin123`

> 首次启动自动创建 MySQL 数据库 `ops_platform` 和默认管理员。

---

## 项目结构

```
app/
├── static/
│   ├── style.css              # 全局样式（企业级 UI 主题）
│   ├── dialog.js              # 通用弹窗组件（Modal）
│   ├── table.js               # 表格排序 + 分页组件（TableKit）
│   └── filter.js              # 搜索栏交互增强
├── templates/
│   ├── base.html              # HTML 基础模板
│   ├── layout.html            # 侧边栏 + 顶栏 + 内容区布局
│   ├── login.html             # 登录页
│   ├── dashboard_home.html    # 仪表盘
│   ├── assets.html            # 主机管理（弹窗表单）
│   ├── asset_detail.html      # 资产详情
│   ├── containers.html        # 容器管理 - 集群列表
│   ├── pods.html              # 容器管理 - Pod 列表
│   ├── services.html          # 容器管理 - Service 列表
│   ├── monitoring.html        # 监控指标管理
│   ├── monitoring_host.html   # 主机监控列表
│   ├── monitoring_host_detail.html  # 主机监控详情（圆形进度条）
│   ├── reports.html           # 报表中心首页
│   ├── report_detail.html     # 预置报表详情
│   ├── report_custom.html     # 自定义报表
│   ├── report_schedule.html   # 定时发送配置
│   ├── tickets.html           # 工单协作（弹窗表单）
│   ├── ticket_detail.html     # 工单详情
│   ├── alerts.html            # 告警中心（弹窗表单）
│   ├── alert_detail.html      # 告警详情
│   ├── audit.html             # 审计日志
│   ├── users.html             # 用户管理（弹窗表单）
│   ├── roles.html             # 角色权限（弹窗表单 + 分配菜单树形弹窗）
│   ├── password.html          # 修改密码
│   └── forbidden.html         # 无权限页
├── db/                        # 数据库连接与初始化
├── models/
│   ├── asset.py               # 资产模型
│   ├── container.py           # 容器模型（集群/Deployment/Pod/Service）
│   ├── monitoring.py          # 监控模型（指标定义/数据点）
│   ├── ticket.py              # 工单模型
│   ├── alert.py               # 告警模型
│   ├── audit.py               # 审计日志模型
│   ├── user.py                # 用户模型
│   ├── rbac.py                # 角色权限模型
│   └── dashboard.py           # 仪表盘数据结构
├── api/                       # REST API 路由
├── routes_auth.py             # 登录路由
├── routes_pages.py            # 后台页面路由（所有页面）
├── services_assets.py         # 资产服务
├── services_containers.py     # 容器管理服务
├── services_monitoring.py     # 监控告警服务
├── services_reports.py        # 报表服务
├── services_tickets.py        # 工单服务
├── services_alerts.py         # 告警服务
├── services_audit.py          # 审计日志服务
├── services_users.py          # 用户服务
├── services_roles.py          # 角色 / 权限服务
├── services_permissions.py    # 权限判断与统一封装
└── services_auth.py           # 认证服务
```

---

## 本地启动

```bash
cd ~/.openclaw/my-project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开：
- 登录页：`http://localhost:8000/login`
- 首页：`http://localhost:8000/`
- API 文档：`http://localhost:8000/docs`

数据库：MySQL `ops_platform`（启动时自动建库建表）

默认连接：`localhost:3306`，`root` / `123456`

---

## REST API（v1）

所有 API 以 `/api/v1` 为前缀，统一返回格式：

```json
{ "code": 0, "msg": "ok", "data": { ... } }
```

认证方式：`Authorization: Bearer <token>`（JWT）

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 登录，返回 JWT |
| GET | `/api/v1/auth/me` | 当前用户信息 + 权限 |
| POST | `/api/v1/auth/logout` | 登出 |

### 仪表盘

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboard/stats` | 核心指标数据 |
| GET | `/api/v1/dashboard/summary` | 综合概览（动态、分布等） |

### 资产管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/assets/` | 资产列表（支持 keyword/type/status 筛选） |
| POST | `/api/v1/assets/` | 新增资产 |
| GET | `/api/v1/assets/{id}` | 资产详情 |
| PUT | `/api/v1/assets/{id}` | 编辑资产 |
| DELETE | `/api/v1/assets/{id}` | 删除资产 |

### 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/users/` | 用户列表 |
| POST | `/api/v1/users/` | 新增用户 |
| GET | `/api/v1/users/{id}` | 用户详情 |
| PUT | `/api/v1/users/{id}` | 编辑用户 |
| DELETE | `/api/v1/users/{id}` | 删除用户 |
| GET | `/api/v1/users/meta/roles` | 角色列表（表单用） |

### 角色权限

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/roles/` | 角色列表 |
| POST | `/api/v1/roles/` | 新增角色 |
| GET | `/api/v1/roles/{id}` | 角色详情 |
| PUT | `/api/v1/roles/{id}` | 编辑角色 |
| DELETE | `/api/v1/roles/{id}` | 删除角色 |
| PUT | `/api/v1/roles/{id}/permissions` | 分配菜单权限 |
| GET | `/api/v1/roles/meta/permission-tree` | 权限树结构 |

### 工单 / 告警 / 容器 / 监控 / 报表 / 审计 / 密码

均遵循相同模式：`GET /` 列表、`POST /` 创建、`GET /{id}` 详情、`PUT /{id}` 编辑、`DELETE /{id}` 删除。

详见 Swagger 文档：`http://localhost:8000/docs`

---

## 架构说明

项目支持 **双模式运行**：
- **SSR 模式**（现有）：FastAPI + Jinja2 服务端渲染，适合快速部署
- **前后端分离**（已支持）：后端纯 REST API，前端可对接 Vue/React SPA

两种模式共存，API 和页面路由互不干扰。

---

## 接下来建议

### 进行中

- ✅ **REST API 层** — 全部模块 API 已就绪（60+ 接口）
- ✅ **JWT 认证** — 登录/鉴权/权限校验
- ✅ **CORS** — 已配置，支持前端跨域开发
- 🔲 **前端 SPA** — Vue 3 + Element Plus 前端开发

### 短期优化

- **监控数据对接** — 主机监控对接 Linux 命令（top/df/free/proc）采集真实数据
- **告警联动** — 监控指标超阈值自动生成告警记录
- **定时发送后端** — 完成报表定时邮件发送的后端逻辑
- **批量操作** — 列表页多选批量删除、批量状态变更
- **工单流转增强** — 工单评论、附件上传、处理时间统计

### 中期扩展

- **通知系统** — 多渠道通知（邮件/短信/钉钉/站内信/Webhook）
- **更细粒度权限** — 数据范围权限、组织架构维度
- **资产关系** — 资产拓扑图、关联关系可视化
- **PDF/Excel 导出** — 报表导出为 PDF 和 Excel 格式

### 长期规划

- **数据库演进** — Alembic 迁移管理，支持 PostgreSQL
- **监控增强** — 对接 Prometheus/Zabbix，历史趋势图表
- **容器深度集成** — 对接 K8s API，实时 Pod 日志、Exec
- **移动端适配** — 响应式优化或独立移动端页面
- **多租户** — 组织架构隔离、数据权限隔离
