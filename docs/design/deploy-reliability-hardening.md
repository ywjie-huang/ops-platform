# 应用发布模块修复与加固设计

| 项目 | 内容 |
|---|---|
| 状态 | 待评审 |
| 日期 | 2026-08-14 |
| 依赖 | 现有 deploy 模块（`services/deploy/` + `api/deploy.py` + 前端 7 views） |
| 涉及模块 | `services/deploy/strategies/`、`services/deploy/records.py`、`services/deploy/builder.py`、`models/deploy.py`、`api/deploy.py`、`db/init_db.py` |
| 关联文档 | `docs/superpowers/specs/2026-07-13-jenkins-release-integration-design.md`（模式 B 权威 spec，**本设计不覆盖**，仅在 §7 说明衔接关系） |
| 前置缺陷引入 | commit `0af3687`（健康检查下放环境级时漏改 Docker/K8s 策略） |

---

## 1. 背景与目标

应用发布模块骨架完整（3 种部署策略 × 3 种构建模式 + 审批 + 回滚 + 构建版本库），但存在：

- **两个必挂 bug**：Docker / K8s 部署策略引用已删除的字段，每次执行必然 AttributeError 失败，实际只有 SSH 策略可用
- **可靠性欠账**：部署跑在 daemon 线程，后端重启任务即丢且记录永久停留中间态；同应用同环境可并发触发互相踩；Jenkins 构建号超时后「猜」lastBuild 可能跟错
- **零测试**：整个 deploy 模块（约 5000+ 行）没有一行测试

**目标**：把现有三条策略路修通、走稳——修复致命 bug、补上可靠性机制、建立测试基线。

**非目标**（本设计不做）：

- 不实现模式 B（release_mode / Job 参数契约 / Jenkins 回调）——那属于关联 spec 的范畴，见 §7
- 不做多级审批、多 Jenkins 实例、灰度发布、部署窗口
- 不改前端页面结构（仅 §4.4 可选项涉及前端一行改动）

## 2. 现状盘点

### 2.1 已有能力（不动）

| 能力 | 位置 | 状态 |
|---|---|---|
| SSH 部署策略 | `strategies/ssh_strategy.py` | ✅ 完整可用（时间戳文件名 + 软链 + 脚本 + TCP/HTTP 健康检查） |
| Docker / K8s 部署策略 | `strategies/docker_strategy.py` / `k8s_strategy.py` | ❌ 必挂（见 §3.1） |
| 构建三模式 upload/webhook/jenkins | `builder.py` / `webhook.py` | ✅ jenkins 走模式 C 全链路 |
| 单级审批（prod 默认开） | `approvals.py` + `api/deploy.py:1013` | ✅ 通过后自动触发部署 |
| 回滚（上次成功 / 指定构建） | `api/deploy.py:716` + `records.py:172-203` | ✅ 快照机制 |
| 构建版本库（tag/pin/清理/比较） | `webhook.py` + `api/deploy.py:1246+` | ✅ |
| 产物 webhook（HMAC 强制） | `webhook.py:22-53` | ✅ 默认关闭 + `SECURITY_CONTROLS.deploy_webhook` |

### 2.2 问题清单（按优先级）

| # | 级别 | 问题 | 位置 |
|---|---|---|---|
| P0-1 | **致命** | Docker/K8s 策略读 `app.health_check_url/timeout`，字段已在环境级重构中删除 → 每次必 AttributeError | `docker_strategy.py:49-50`、`k8s_strategy.py:64-65` |
| P0-2 | 高 | `deploy_builds` 的 `UniqueConstraint(app_id, build_number)` 只在注释里，从未建约束；并发 webhook 可能产生重复构建号 | `models/deploy.py:228-229` |
| P0-3 | 中 | cleanup-config 标着「按应用」实际读写全局 `system_config`，语义骗人 | `api/deploy.py:1710-1786` |
| P1-1 | 高 | 同一 app+env 无并发锁，可同时触发两次部署互相覆盖 | `api/deploy.py:641`（execute 无占用检查） |
| P1-2 | 高 | daemon 线程执行 + `_cancel_flags` 内存 dict：后端重启 → 执行线程消失，记录永久停留 building/deploying，无任何收敛 | `records.py:18,136` |
| P1-3 | 高 | Jenkins 触发后 `_wait_for_build_start` 超时 120s 则 fallback `lastBuild` —— 可能拿到别人的构建号，产物错配 | `builder.py:236-243` |
| P1-4 | 低 | 后端已有真 SSE 日志端点 `GET /records/{id}/log`，前端却用 1s 轮询（函数名叫 startSSE 名不副实） | `api/deploy.py:894`、`DeployDetailView.vue:192-215` |
| P1-5 | 中 | webhook 构建模式下走普通 `/execute`（不带 build_number）会因快照无产物路径而失败，用户必须走「部署构建版本」入口——行为割裂且无提示 | `records.py:209-229`、`api/deploy.py:641` |
| P2-1 | 中 | 整个模块零测试 | `backend/tests/` 无 deploy 文件 |

## 3. P0 修复设计

### 3.1 Docker / K8s 策略健康检查字段修复

**根因**：commit `0af3687` 把健康检查配置从应用级（`DeployApplication.health_check_url` 等字段）下放到环境级（`DeployAppEnv.health_check_url/port/timeout`，`models/deploy.py:83-85`），SSH 策略同步改了，Docker/K8s 策略漏改，引用了不存在的属性。

**修复**：两处策略函数把

```python
app.health_check_url, app.health_check_timeout   # AttributeError
```

改为从 `app_env` 读取：

```python
app_env.health_check_url, app_env.health_check_port, app_env.health_check_timeout
```

**顺带统一**（低成本高收益）：三个策略各自实现了一遍健康检查。把 SSH 策略里已有的「TCP 端口优先、HTTP URL 兼容」逻辑（`ssh_strategy.py:207-226`）抽到 `strategies/base.py` 作为共享函数：

```python
def check_health(app_env, ssh_client=None) -> tuple[bool, str]
```

- 有 `health_check_port` → TCP 探测（Docker/K8s 场景无 SSH 时用本地 socket 直连）
- 有 `health_check_url` → HTTP GET（带 timeout）
- 都没有 → 跳过健康检查（视为通过，日志注明「未配置健康检查」）

三个策略统一调用，后续加策略不再各写一套。

### 3.2 builds 唯一约束落地

`models/deploy.py:228-229` 的 `UniqueConstraint("app_id", "build_number")` 从注释变成真实约束。项目已有自动迁移机制（`init_db()` 启动时 ALTER TABLE），按现有模式追加：

```sql
ALTER TABLE deploy_builds ADD UNIQUE INDEX uq_deploy_builds_app_build (app_id, build_number);
```

**注意**：建唯一索引前先清洗存量重复数据（同 app 下重复 build_number 保留 id 最大者，其余改 `build_number = build_number * -1`（墓碑）或直接删除——推荐删除，build_number 无外键引用，`deploy_records` 快照里存的是 JSON 值不受影响）。清洗逻辑写在 `init_db.py` 的迁移段，幂等。

应用层 `create_build_record`（`webhook.py:205`）的查重 upsert 保留——约束是兜底不是替代（防并发窗口）。

### 3.3 cleanup-config 归属修正

两个方向二选一，推荐 A：

- **A（推荐）· 改文案为全局**：清理配置本来就是全局语义（`deploy.keep_build_count/days`），把前端 UI 文案和 API 描述改为「全局构建清理配置」，从 AppDetail 移到系统设置或部署记录页。改动小，语义诚实。
- **B · 真按应用**：`deploy_applications` 加 `keep_build_count`/`keep_build_days` 可空列，为空回退全局。适合不同应用保留策略差异大的场景。

## 4. P1 可靠性加固设计

### 4.1 app+env 并发锁（互斥）

**现状**：`POST /deploy/execute` 无任何占用检查，同 app+env 可同时触发两次，两个 daemon 线程写同一目标。

**设计**：双层防护。

**第一层（API 入口，主防线）**：execute / rollback / builds/{bn}/deploy 入口统一走一个检查函数：

```python
def ensure_no_active_deploy(db, app_id: int, env_id: int, exclude_record_id: int | None = None):
    """同 app+env 存在进行中记录（含待审批）时抛 DeployConflictError。"""
    # status IN ('pending', 'building', 'deploying')
    # 或存在 status='pending' 的关联审批（approval 未决 = 占用中）
```

返回 409 语义（`{"code": 1, "msg": "该应用在此环境已有进行中的部署（记录 #123，状态 building）"}`），前端 ElMessage 提示。

**第二层（线程启动前，竞态兜底）**：API 检查与线程启动之间仍有微小时窗（审批通过的自动触发路径尤其要防），`execute_deploy` 线程开头再查一次，冲突则直接置 `failed`（附注「并发冲突」）。

**不做**：分布式锁（单实例部署，进程内检查 + DB 状态查询足够；将来多副本时再把第一层改成 `SELECT ... FOR UPDATE`）。

### 4.2 重启恢复（僵尸任务收敛）

**现状**：部署在 daemon 线程跑（`records.py:136`），后端重启 → 线程蒸发，`deploy_records` 永久停留 `building`/`deploying`；`_cancel_flags` 内存 dict 同步蒸发。

**设计**：不追求断点续跑（部署动作不可幂等重放），只做**启动收敛**：

在 `init_db()` 之后（或 startup lifespan 中）执行 `recover_interrupted_deploys()`：

```python
UPDATE deploy_records
SET status = 'failed',
    finished_at = now,
    log = concat(coalesce(log, ''), '\n[系统] 后端重启，部署被中断，请重新发起')
WHERE status IN ('building', 'deploying')
```

同时清空内存 `_cancel_flags`（重启后必然为空，防御性重建）。

**pending 状态不收敛**：pending 且无审批 = 尚未开始，重启后由触发它的 HTTP 请求生命周期决定——实际上 execute 是同步起线程，pending 只在审批流存在（等审批的记录 status=pending）。等审批的记录不受重启影响（数据都在 DB），无需处理。

**取消标志持久化**：`cancel` 端点已把 DB status 置 `cancelled`，线程内的 `_cancel_flags` 只是加速检查。改造：策略循环里的取消检查点（上传分块、轮询间隙）同时读内存标志 **或** DB status——这样「取消」在重启场景也不失效。实现上给 records.py 加 `_is_cancelled(db, record_id)` 融合函数。

### 4.3 Jenkins 构建号追踪（去掉 lastBuild 猜测）

**现状**：`_wait_for_build_start` 轮询 queue item 120s，超时后 fallback `lastBuild`（`builder.py:236-243`）——如果队列拥堵或有并发构建，`lastBuild` 可能是**别人的**构建，下载错产物。

**设计**：**超时即失败，不猜**。

1. 触发后从响应头 `Location` 拿 queue item URL（现有逻辑已拿）
2. 轮询 `GET /queue/item/{id}/api/json` 直到出现 `executable.number`（现有逻辑）
3. 超时（120s）→ `raise DeployError("Jenkins 构建排队超时（120s 未开始），请检查 Jenkins 执行器；已放弃追踪，未下载任何产物")`
4. 删除 `lastBuild` fallback 分支

配套：把拿到的 build_number 写入 `deploy_records.deploy_config` 快照（`jenkins_build_number` 键）与 `deploy_builds.build_number`，全链路可追溯「这次部署用的是哪个构建」。

### 4.4 前端日志接入真 SSE（可选，半小时）

后端 `GET /deploy/records/{id}/log` 已是真 SSE（`api/deploy.py:894`）。前端 `DeployDetailView.vue:192-215` 的 `startSSE`（实为 1s 轮询）改为消费该端点：`new EventSource()`，done 事件时关闭。失败时回退轮询（保持现有逻辑为 fallback）。收益：部署日志流式呈现（Jenkins 控制台回显本来就是流式的），降低无谓轮询。

### 4.5 webhook 模式直发失败引导（小改）

`POST /deploy/execute` 在 `build_mode=webhook` 且请求未带 build_number 时，不再等到执行线程里失败，而是入口直接返回：

```json
{"code": 1, "msg": "该应用为 webhook 构建模式，请从「构建历史」选择版本发起部署"}
```

同时在 `AppDetailView` 环境卡片的部署确认弹窗里，webhook 模式应用把「部署」按钮改为引导跳转到构建历史 Tab（或直接弹「选择构建版本」对话框，复用现有 builds/{bn}/deploy 弹窗）。

## 5. 测试计划（从零补齐）

| 层 | 用例 | mock 方式 |
|---|---|---|
| 策略单测（新 `test_deploy_strategies.py`） | Docker/K8s 策略健康检查字段从 app_env 读取（**P0-1 回归**：断言不再访问 app 上的已删字段）；`check_health` TCP/HTTP/未配置三分支 | mock paramiko SSH、httpx、K8s `_request` |
| 并发锁（`test_deploy_concurrency.py`） | 同 app+env 有 building 记录时 execute 返回冲突；审批 pending 占用；不同 env 不互斥；`ensure_no_active_deploy(exclude_record_id)` 放行自身 | SQLite 内存库，直接调函数 |
| 重启恢复（同上文件） | building/deploying 记录被收敛为 failed 且 log 带中断标注；pending 不受影响；幂等（二次执行无变化） | 直接调 `recover_interrupted_deploys` |
| 构建号（`test_deploy_builder.py`） | queue 轮询拿到 executable.number 后正常下载；超时 raise（**无 lastBuild fallback 回归**） | mock httpx 流程序列 |
| webhook（`test_deploy_webhook.py`） | HMAC 签名校验通过/拒绝/常量时间；`create_build_record` 幂等（同 commit 二次推送不新建） | 现有 FakeClient 模式 |
| 唯一约束（`test_deploy_models.py`） | 同 app 同 build_number 二次插入抛 IntegrityError | SQLite 内存库建表 |

测试风格遵循仓库现有模式（in-memory SQLite + monkeypatch + 直接调 service 函数，参照 `test_ai_tools.py`）。

## 6. 实施步骤与工作量

| 阶段 | 内容 | 预估 |
|---|---|---|
| 1 | P0-1 字段修复 + check_health 抽取 + 策略单测 | 半天 |
| 2 | P1-1 并发锁 + P1-2 重启恢复 + 对应测试 | 1 天 |
| 3 | P1-3 构建号追踪 + P1-4 SSE + P1-5 webhook 引导 | 半天 |
| 4 | P0-2 唯一约束（含存量清洗）+ P0-3 cleanup 文案 + 模型测试 | 半天 |

合计约 **2.5 天**。阶段 1-4 相互独立，可拆开提交；建议顺序执行（1 最急——Docker/K8s 用户当前完全不可用）。

## 7. 与模式 B spec 的衔接（本期不做）

关联 spec（`2026-07-13-jenkins-release-integration-design.md`）定义的模式 B（治理触发：Jenkins Job 接平台参数、回调通知、平台管状态）**不在本设计范围**。但本设计的几项改动是模式 B 的直接前置：

| 本期改动 | 模式 B 复用点 |
|---|---|
| §4.1 并发锁 | spec 的「app+env 互斥」Phase 1 项，原样复用 |
| §4.2 重启收敛 | spec 的「启动僵尸任务收敛」Phase 1 项；模式 B 的 `triggering` 状态纳入同一收敛集合即可 |
| §4.3 构建号追踪 | spec 的 Job 参数契约（RECORD_ID/RELEASE_MODE）落地时，回调对账依赖「平台记录的构建号」 |
| §3.1 check_health 统一 | 模式 B 下部署由 Jenkins 执行，平台侧健康检查逻辑复用同一函数 |

即：**本期加固完成后，模式 B 落地时只需新增 release_mode 分流与回调端点，不需要重做可靠性层**。

## 8. 风险与边界

| 风险 | 缓解 |
|---|---|
| 唯一索引建立时存量重复数据导致迁移失败 | §3.2 先清洗后建索引，清洗幂等；迁移包 try/except 记日志不阻断启动（与现有 ALTER TABLE 容错风格一致） |
| 重启收敛误伤「执行极慢但线程还活着」的记录 | 不存在该场景：线程与进程同生命周期，进程重启线程必死。收敛仅由启动动作触发一次 |
| 去掉 lastBuild 兜底后，Jenkins 队列慢的场景更容易失败 | 120s 队列超时对常规任务足够；超时明确报错比静默拿错产物好——错误可重试，产物错配难发现 |
| 并发锁引入「卡死占用」 | 占用状态全部来自 DB 记录状态，任何终态（success/failed/cancelled）自动释放；重启收敛兜底 |
| Docker/K8s 修复后策略首次真实执行可能暴露下游问题（此前从未跑通过） | 建议修完先在 dev 环境各走一轮完整部署再放开发；日志全程落 `deploy_records.log` 可回溯 |
