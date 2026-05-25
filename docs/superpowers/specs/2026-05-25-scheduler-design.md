# 定时任务框架设计

## 概述

为运维管理平台添加定时任务调度能力，基于 APScheduler 实现，使用内存调度 + DB 自有模型的方案。

## 目标

- 支持 cron 表达式定义定时任务
- 首批内置任务：定时巡检
- 预留扩展点：定时报表、定时备份
- 前端可管理任务（增删改查、启停、立即执行、查看执行日志）
- 不引入 Redis/Celery 等外部依赖

## 方案选择

**采用方案 B：内存调度 + DB 自有模型**

- APScheduler 使用内存 jobstore，不依赖其内部 DB 表结构
- 任务定义存储在自有的 `scheduled_tasks` 表
- 启动时从 DB 加载 enabled 任务注册到 scheduler
- UI 改动 → 更新 DB → 单向同步到 scheduler 内存
- 执行日志写自有的 `task_execution_logs` 表

理由：数据模型完全自控，UI 和调度器之间只需 DB → memory 单向同步，避免双向同步的不一致问题。

## 数据模型

### scheduled_tasks

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增 |
| name | str(100) | 任务名称 |
| task_type | str(50) | 任务类型标识（patrol / report / backup） |
| cron_expr | str(100) | cron 表达式，如 `0 2 * * *` |
| params | JSON | 任务参数，不同 task_type 结构不同 |
| enabled | bool | 启用/禁用 |
| description | str(500) | 备注说明 |
| last_run_at | datetime | 最近执行时间 |
| last_status | str(20) | success / failed / running |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### task_execution_logs

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增 |
| task_id | int FK → scheduled_tasks.id | 关联任务 |
| started_at | datetime | 开始时间 |
| finished_at | datetime | 结束时间 |
| status | str(20) | success / failed |
| result | text | 结果摘要 |
| error | text | 失败时的错误信息 |

## 后端架构

### 新增文件

| 文件 | 职责 |
|------|------|
| `backend/app/core/scheduler.py` | 调度器初始化、startup/shutdown 生命周期 |
| `backend/app/models/scheduled_task.py` | ScheduledTask + TaskExecutionLog 两个 SQLAlchemy model |
| `backend/app/services/scheduler.py` | 任务执行服务：注册、启停、执行回调、执行日志写入 |
| `backend/app/api/scheduler.py` | REST API 路由 |

### 调度器核心（core/scheduler.py）

- `AsyncIOScheduler` 内存模式
- `TASK_REGISTRY: dict[str, Callable]` 任务类型 → 执行函数映射
- startup 时从 DB 加载 enabled 任务，调用 `add_job()` 注册
- shutdown 时优雅关闭
- 首批注册：`patrol` → `patrol_service.run_patrol()`

### 执行回调

每个 job 执行时：
1. 创建 `TaskExecutionLog` 记录（status=running）
2. 更新 `ScheduledTask.last_status` = running
3. 调用对应 task_type 的执行函数
4. 成功：更新 log status=success, result=摘要；更新 task last_run_at/last_status=success
5. 失败：更新 log status=failed, error=错误信息；更新 task last_status=failed
6. 异常不向上抛出，不中断调度器

### API 路由

前缀：`/api/v1/scheduler`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /tasks | 任务列表（分页） |
| POST | /tasks | 创建任务 |
| PUT | /tasks/{id} | 更新任务（同步到 scheduler） |
| DELETE | /tasks/{id} | 删除任务（从 scheduler 移除） |
| POST | /tasks/{id}/toggle | 启用/禁用切换 |
| POST | /tasks/{id}/run | 立即执行一次 |
| GET | /tasks/{id}/logs | 查看执行日志（分页） |

## 前端

### 路由

新增路由 `/settings/scheduler`，在侧边栏"系统设置"菜单下作为子项。

### 新增文件

- `frontend/src/views/settings/SchedulerView.vue`
- `frontend/src/api/scheduler.ts`

### 页面功能

- 任务列表表格：名称、类型、cron 表达式、启用状态（switch）、上次执行时间/状态、操作按钮
- 新建/编辑弹窗：名称、任务类型下拉、cron 表达式输入、参数表单（按 task_type 动态切换）、备注
- 执行日志抽屉：点击"查看日志"展开表格
- "立即执行"按钮：触发后轮询刷新

### task_type 参数

- `patrol`：无额外参数
- `report`（预留）：选择报表模板
- `backup`（预留）：备份路径、保留天数

## 依赖

- 新增 `apscheduler>=3.10.0` 到 requirements.txt

## 实施范围

首批实现：
- 框架搭建（调度器核心、模型、API、前端页面）
- 定时巡检任务完整跑通

预留不实现：
- 定时报表生成
- 定时数据库备份
