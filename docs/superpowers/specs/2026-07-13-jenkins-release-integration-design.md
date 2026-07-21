# Jenkins 发布接入设计

> 状态：Draft  
> 日期：2026-07-13  
> 范围：应用发布模块与现有 Jenkins 流水线的集成策略、接口契约、数据模型与分期落地  
> 关联文档：
> - `DEPLOY.md` — 应用发布使用说明
> - `docs/design/jenkins-integration.md` — 早期「平台拉产物并部署」方案（本文件对其做策略修正）
> - `docs/system-comprehensive-assessment.md` — 安全与可靠性基线

---

## 1. 背景与问题

平台已具备应用发布骨架：应用 / 环境 / 审批 / 记录 / SSH·Docker·K8s 策略，以及 `build_mode=jenkins` 的触发与产物下载能力。与此同时，线上已有一套可工作的 **Jenkins 构建 + 部署** 流水线。

当前真正的问题不是“能不能接 Jenkins”，而是：

1. **职责边界不清**：平台既想像 CD 一样部署，又没有足够可靠的任务执行与产物一致性；
2. **双入口风险**：Jenkins 与平台都能发版时，版本、审批、审计会对不上；
3. **替换成本高**：把现有 Jenkins 部署步骤拆掉、改由平台 SSH/Docker/K8s 接管，等于重做一半 CD；
4. **现有深接入实现偏重**：`builder.py` 已实现「触发 → 轮询 → 下载 artifact → 平台部署」，更接近全量接管，不适合作为现网默认路径。

因此需要一份明确的接入设计：**先治理，后接管；先浅接入，后深试点。**

---

## 2. 目标与非目标

### 2.1 目标

| 优先级 | 目标 | 说明 |
|--------|------|------|
| P0 | 统一发布入口 | 运维在平台发起/审批发布，不必先找 Jenkins 权限与页面 |
| P0 | 保留现网 Jenkins 能力 | 不打断已有构建、部署、通知、回滚习惯 |
| P0 | 可审计 | 谁、何时、哪个应用/环境、哪个 Job/Build、结果是什么，平台可查 |
| P1 | 与资产/工单/审批联动 | 发布单可关联环境、审批人、失败后可转工单 |
| P2 | 为后续平台部署留扩展点 | 不堵死「Jenkins 只构建、平台部署」的演进 |

### 2.2 非目标（本阶段明确不做）

- 用平台完整替代 Jenkins CD
- 在平台内解析/编辑 Jenkinsfile
- 多 Jenkins 集群联邦、流水线可视化编排
- 生产环境默认走平台 Docker `stop/rm/run` 或未经验证的 K8s 接管
- 把数据库迁移、复杂多服务编排搬进平台策略层

---

## 3. 设计原则

1. **Jenkins 继续做它擅长的事**：编译、测试门禁、打包、（现网）部署脚本。
2. **平台做发布治理**：权限、审批、环境选择、操作审计、状态聚合、与 CMDB/工单联动。
3. **同一应用同一环境只允许一个权威发布入口**，避免双写双发。
4. **契约优于耦合**：平台与 Jenkins 只通过稳定参数和状态回调/轮询交互，不依赖 Job 内部实现细节。
5. **先可回退**：任何阶段都应能一键退回“只在 Jenkins 操作”，平台侧降级为只读记录。
6. **安全默认关闭高风险能力**：产物 Webhook、未鉴权回调等默认禁用，显式开启并校验。

---

## 4. 接入模式定义

### 4.1 模式总览

| 模式 | 名称 | 构建 | 部署 | 平台职责 | 适用阶段 |
|------|------|------|------|----------|----------|
| A | 只读关联 | Jenkins | Jenkins | 记录链接 / 展示 | 可选，几乎无改动 |
| **B** | **治理触发（推荐默认）** | **Jenkins** | **Jenkins** | **申请、审批、触发、状态、审计** | **Phase 1 主路径** |
| C | 构建分离 | Jenkins | 平台 | 触发构建、拉产物、执行策略 | Phase 2 非生产试点 |
| D | 全自建 | 平台/其他 | 平台 | 完整 CD | 不在本设计范围 |

### 4.2 模式 B — 治理触发（默认）

```text
用户在平台选择 应用 / 环境 / 版本
        |
        v
  环境需要审批？ --是--> 审批通过后继续
        |否
        v
  平台调用 Jenkins buildWithParameters
  (APP_NAME / ENV / VERSION / OPERATOR / RECORD_ID ...)
        |
        v
  Jenkins 执行既有 Pipeline（构建 + 部署 + 通知）
        |
        |-- 平台轮询 Job/Build 状态
        +-- （可选）Jenkins post 回调平台更新结果
        |
        v
  平台更新 DeployRecord，写入审计；可跳转 Jenkins 控制台
```

**关键点：平台不下载产物，不执行 SSH/Docker/K8s 部署。**  
发布是否成功，以 Jenkins Build 结果（及可选回调）为准。

### 4.3 模式 C — 构建分离（试点）

```text
平台触发 Jenkins（仅构建 + archiveArtifacts）
        |
        v
  平台下载产物 -> 写入 Artifact 库（含 sha256）
        |
        v
  平台按 DeployRecord 快照执行 SSH/Docker/K8s 策略
        |
        v
  健康检查 -> success/failed；回滚基于快照重放
```

仅用于：

- 明确改造为「只构建不部署」的 Job；
- 非生产环境；
- 单一应用试点，验证产物一致性与部署可靠性后再扩面。

### 4.4 模式选择规则

```text
应用配置 release_mode:
  - jenkins_governed   -> 模式 B（默认）
  - jenkins_build_only -> 模式 C（需显式开启 + 环境白名单）
  - upload             -> 既有上传产物部署（与 Jenkins 无关）
```

> 说明：现有代码里的 `build_mode=jenkins` 语义接近模式 C。  
> 落地时建议新增 `release_mode`（或等价字段）区分 B/C，避免继续把“触发 Jenkins”和“平台部署”绑死。

---

## 5. 总体架构

```text
+----------------------------------------------------------+
|                     运维平台（治理面）                      |
|                                                          |
|  应用发布 UI                                              |
|    |- 应用/环境/版本                                       |
|    |- 审批（prod）                                         |
|    |- 发布单详情 / 日志 / 跳转 Jenkins                      |
|    +- 审计 / 可选转工单                                    |
|              |                                           |
|              v                                           |
|  Deploy Orchestrator                                      |
|    |- ReleaseMode = jenkins_governed  --> Jenkins Client  |
|    |       trigger + poll + (callback)                    |
|    |- ReleaseMode = jenkins_build_only --> Builder        |
|    |       trigger + artifact + Strategy                  |
|    +- ReleaseMode = upload ------------> Strategy only    |
+---------------|------------------------------------------+
                | REST
                v
+------------------------------------------+
|              Jenkins（执行面）             |
|  Job: build / test / (deploy) / notify   |
|  参数: APP_NAME ENV VERSION ...          |
|  产物: archiveArtifacts（模式 C 需要）    |
+------------------------------------------+
```

**一句话：平台是控制面，Jenkins 是执行面（模式 B）；模式 C 才把部署执行面迁到平台。**

---

## 6. 职责边界

| 事项 | 模式 B（默认） | 模式 C（试点） |
|------|----------------|----------------|
| 代码检出 / 编译 / 单测 | Jenkins | Jenkins |
| 制品归档 | Jenkins（可无平台消费） | Jenkins 必须 archive |
| 部署到主机/K8s | **Jenkins** | **平台策略** |
| 健康检查 | Jenkins（或脚本内） | 平台 |
| 发布审批 | 平台 | 平台 |
| 操作审计 | 平台 | 平台 |
| 回滚 | Jenkins rollback Job 或平台触发同一 Job 的回滚参数 | 平台基于历史快照重部署 |
| 密钥/部署凭据 | 仍在 Jenkins Credentials | 平台资产 SSH/K8s Token |
| 失败通知 | 可沿用 Jenkins；平台可二次通知 | 平台为主 |

### 6.1 禁止事项

- 同一 `app + env` 同时配置“平台自动部署”和“Jenkins 自动部署”且都可手动触发；
- 模式 B 下平台再去 SSH 改同一批机器（除非独立的应急入口且权限隔离）；
- 模式 C 下 Jenkins Pipeline 仍保留生产部署 stage（会造成双发）。

---

## 7. Job 契约

### 7.1 触发参数（平台 -> Jenkins）

所有模式 B/C 的 Job 建议统一接收以下参数（缺失时 Jenkins 侧用默认值，但平台尽量全传）：

| 参数 | 必填 | 示例 | 说明 |
|------|------|------|------|
| `APP_NAME` | 是 | `order-api` | 平台应用名 |
| `ENV` | 是 | `dev` / `staging` / `prod` | 目标环境 |
| `VERSION` | 否 | `v1.2.3` / `a1b2c3d` | 版本、Tag 或 commit |
| `BRANCH` | 否 | `main` | 构建分支，若 Job 需要 |
| `OPERATOR` | 是 | `zhangsan` | 平台发起人 |
| `RECORD_ID` | 是 | `1024` | 平台部署记录 ID，用于回调关联 |
| `RELEASE_MODE` | 是 | `governed` / `build_only` | 让 Pipeline 知道是否应执行部署 stage |
| `ROLLBACK_FROM` | 否 | `1010` | 回滚时源记录 ID |
| `EXTRA_JSON` | 否 | `{}` | 扩展参数，JSON 字符串 |

触发 API：

```http
POST {JENKINS_URL}/job/{job_name}/buildWithParameters
Authorization: Basic base64(user:token)
Content-Type: application/x-www-form-urlencoded

APP_NAME=order-api&ENV=staging&VERSION=v1.2.3&OPERATOR=zhangsan&RECORD_ID=1024&RELEASE_MODE=governed
```

### 7.2 模式 B Pipeline 约定

- 保留现有构建 + 部署逻辑；
- 读取 `ENV` / `VERSION` 决定部署目标；
- `post` 中尽量调用平台回调（见 8.3）；
- 不要求 `archiveArtifacts`（有更好，便于追溯）。

伪代码：

```groovy
pipeline {
  agent any
  parameters {
    string(name: 'APP_NAME')
    string(name: 'ENV')
    string(name: 'VERSION')
    string(name: 'OPERATOR')
    string(name: 'RECORD_ID')
    string(name: 'RELEASE_MODE', defaultValue: 'governed')
  }
  stages {
    stage('Build') { steps { /* 现有构建 */ } }
    stage('Deploy') {
      when { expression { return params.RELEASE_MODE == 'governed' } }
      steps { /* 现有部署 */ }
    }
  }
  post {
    always {
      // 可选：回调平台更新发布单终态
      // POST /api/v1/deploy/jenkins/callback
      // Header: X-Deploy-Token
      // Body: record_id, job, build_number, result, version
    }
  }
}
```

### 7.3 模式 C Pipeline 约定

- `RELEASE_MODE=build_only` 时 **禁止** Deploy stage；
- **必须** `archiveArtifacts`；
- 建议 fingerprint，便于追溯；
- 产物命名稳定，避免每次随机名导致平台匹配失败。

```groovy
post {
  success {
    archiveArtifacts artifacts: 'dist/**/*.jar,target/*.jar', fingerprint: true
  }
}
```

### 7.4 Job 映射规则

| 维度 | 建议 |
|------|------|
| 映射粒度 | 一应用一 Job；或一应用多 Job（按 env 后缀，如 `order-api-prod`） |
| 配置位置 | `DeployApplication.jenkins_job_name`；环境级可覆盖 `DeployAppEnv.jenkins_job_name` |
| 命名 | 与平台应用名可不同，但必须在 UI 展示真实 Job 名 |
| 权限 | Jenkins 侧使用专用 API 用户，最小权限：Job Build/Read + 读 artifacts |

---

## 8. 平台侧设计

### 8.1 配置

#### 全局（系统配置中心）

```json
{
  "url": "https://jenkins.example.com",
  "username": "ops-platform",
  "token": "***",
  "callback_token": "***",
  "default_timeout_sec": 1800,
  "verify_tls": true
}
```

要求：

- Token 脱敏展示；更新时留空表示不修改；
- 提供「测试连接」：请求 `/api/json`，返回版本号；
- 生产环境 `verify_tls=true` 默认开启。

#### 应用 / 环境

| 字段 | 级别 | 说明 |
|------|------|------|
| `release_mode` | 应用（环境可覆盖） | `jenkins_governed` / `jenkins_build_only` / `upload` |
| `jenkins_job_name` | 应用（环境可覆盖） | Job 名 |
| `jenkins_token` | 应用可选 | Job 触发 token（若启用） |
| `allowed_envs_for_build_only` | 应用 | 模式 C 白名单，默认仅 `dev` |
| `jenkins_params_template` | 应用可选 | 额外参数模板 |

### 8.2 发布单状态机

兼容现有状态，并明确模式 B 语义：

```text
pending
  |-(需审批)-> 等待审批
  |              |- 拒绝 -> cancelled
  |              +- 通过 v
  |- triggering   （已调用 Jenkins，等待 queue 分配）
  |- building     （Jenkins building=true；模式 B 下也涵盖其内部 deploy）
  |- deploying    （仅模式 C：平台策略执行中）
  |- success
  |- failed
  +- cancelled
```

模式 B 说明：

- Jenkins 内部的 deploy 不必在平台再拆 `deploying`，可统一用 `building` 或增加展示字段 `jenkins_phase`；
- 对外主状态保持简单，详情里展示 Jenkins build number、result、URL。

### 8.3 回调接口（可选但推荐）

```http
POST /api/v1/deploy/jenkins/callback
Header: X-Deploy-Token: <callback_token>
Content-Type: application/json

{
  "record_id": 1024,
  "job": "order-api",
  "build_number": 88,
  "result": "SUCCESS",
  "version": "v1.2.3",
  "git_commit": "a1b2c3d",
  "artifact_url": "optional",
  "message": "deployed to staging"
}
```

校验：

1. 功能开关（可复用/新增 `ENABLE_DEPLOY_JENKINS_CALLBACK`，默认 false 或与 webhook 同等严格）；
2. `X-Deploy-Token` 与系统配置一致（常量时间比较）；
3. `record_id` 存在且状态为进行中；
4. 幂等：同一 `record_id + build_number + result` 重复回调不重复写审计。

无回调时：平台轮询

```text
GET /job/{name}/{buildNumber}/api/json
```

直到 `building=false` 或超时。

### 8.4 与现有 `build_mode=jenkins` 的关系

| 现有行为 | 问题 | 本设计处理 |
|----------|------|------------|
| 触发 Job 后下载 artifact 并平台部署 | 等同模式 C，不适配现网 Jenkins 已部署场景 | 默认改为模式 B：触发 + 跟状态，不下载、不部署 |
| 无 Location 时用 lastBuild 兜底 | 可能跟错构建号 | 优先 queue id；失败则标记 failed，禁止盲目 lastBuild 当作本次构建 |
| daemon 线程执行 | 重启丢任务 | 见第 11 节可靠性 |

迁移策略：

1. 存量 `build_mode=jenkins` 在配置中标记为 `legacy_build_and_deploy`；
2. 新 UI 默认创建 `jenkins_governed`；
3. 文档与前端文案明确两种模式差异，避免误开模式 C 到 prod。

### 8.5 API 草案（模式 B 核心）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/deploy/execute` | 已有；按 `release_mode` 分流 |
| GET | `/api/v1/deploy/records/{id}` | 增加 jenkins 字段：job、build_number、url、result |
| POST | `/api/v1/deploy/jenkins/callback` | Jenkins 结果回调 |
| POST | `/api/v1/settings/test-connection` service=jenkins | 已有思路，保留 |
| POST | `/api/v1/deploy/apps/{id}/test-job` | 校验 Job 是否存在、是否可读 |
| POST | `/api/v1/deploy/records/{id}/cancel` | 模式 B：尝试 stop Jenkins build（能停则停，不能则只取消平台侧等待） |

权限沿用现有：

- `deploy.execute` 触发
- `deploy.approve` 审批
- `deploy.view` 查看
- `deploy.rollback` 回滚（模式 B 下转为触发 rollback 参数的 Job 或指定 rollback Job）

### 8.6 数据记录

`DeployRecord` / 快照建议固定写入：

```json
{
  "release_mode": "jenkins_governed",
  "jenkins": {
    "url": "https://jenkins.example.com",
    "job_name": "order-api",
    "queue_id": 12345,
    "build_number": 88,
    "build_url": "https://jenkins.example.com/job/order-api/88/",
    "result": "SUCCESS",
    "git_commit": "a1b2c3d",
    "version": "v1.2.3"
  },
  "operator": "zhangsan",
  "env": "staging"
}
```

模式 C 额外：

```json
{
  "artifact": {
    "path": "...",
    "filename": "app.jar",
    "sha256": "...",
    "size": 12345678,
    "source": "jenkins",
    "build_number": 88
  }
}
```

**执行与回滚只认快照，不认环境“当前产物路径”。**  
（修复现有“指定构建版本与策略读取不一致”问题，模式 C 强制要求。）

---

## 9. 前端交互

### 9.1 应用配置

- 构建/发布模式选择：
  - `Jenkins 治理触发（推荐）`
  - `Jenkins 仅构建 + 平台部署（试点）`
  - `上传产物部署`
- 选择模式 B 时：隐藏“平台部署策略必填校验”中与构建产物相关的强制项；展示 Job 名、测试连接/测试 Job。
- 选择模式 C 时：强提示“请确认 Jenkins Job 已移除部署步骤，且仅允许白名单环境”。

### 9.2 发起发布

1. 选环境
2. 填 VERSION / BRANCH（可选）
3. prod 走审批
4. 确认文案随模式变化：
   - B：将触发 Jenkins Job 执行构建与部署
   - C：将触发 Jenkins 构建，成功后由平台部署到目标环境

### 9.3 发布详情

- 状态条 + 平台日志
- Jenkins 信息卡：Job、Build #、结果、耗时、打开 Jenkins 控制台
- 模式 B 不展示“产物下载进度”；模式 C 展示产物与 sha256
- 回滚按钮：
  - B：创建新发布单，参数带上一次成功 VERSION 或 `ROLLBACK=1`
  - C：基于历史快照重部署

---

## 10. 安全设计

| 风险 | 控制措施 |
|------|----------|
| Jenkins Token 泄漏 | 系统配置加密/脱敏；仅管理员可改；不进前端日志 |
| 回调伪造 | 共享 `callback_token`；可选 IP 允许列表；HTTPS |
| 未授权触发发布 | `deploy.execute` + 环境审批；禁止匿名 Webhook 直接部署 |
| 跟错构建号 | 禁止 lastBuild 盲信；必须 queue -> executable.number |
| 模式 C 任意文件写 | 延续评估报告要求：签名、路径白名单、大小限制；默认关 |
| 命令注入 | 模式 C 的 `docker_extra_args`/脚本参数白名单（独立项） |
| 双入口 | 应用切换到平台治理后，Jenkins 手工 Build 权限可收紧为只读+平台账号 |

高危开关建议：

```env
ENABLE_DEPLOY_WEBHOOK=false
ENABLE_DEPLOY_JENKINS_CALLBACK=false
```

---

## 11. 可靠性

### 11.1 执行方式

现状：`threading.Thread(daemon=True)`。

Phase 1 最低要求：

1. 触发 Jenkins 前先落库 `pending/triggering` 与参数快照；
2. 进程启动时扫描超时的 `triggering/building`：
   - 向 Jenkins 查询最终结果并收敛；
   - 无法查询则标记 `failed`，错误信息写「平台重启或轮询中断，请到 Jenkins 核实」；
3. 同一 `app_id + env_id` 加 DB/Redis 互斥锁，禁止并发发布。

Phase 2：迁到任务队列（Celery/RQ/ARQ），支持重试与多实例。

### 11.2 超时

| 阶段 | 默认 | 可配置 |
|------|------|--------|
| 队列等待 | 120s | 是 |
| 构建+部署（模式 B） | 1800s | 是 |
| 仅构建（模式 C） | 600s | 是 |
| 平台部署（模式 C） | 600s | 是 |
| 健康检查 | 30s | 已有 |

### 11.3 取消

- 平台点取消：置 `cancelled`，停止轮询；
- 若已知 `build_number`，尝试 Jenkins `stop`；
- 停止失败不阻塞平台状态收敛，但日志标明“Jenkins 侧可能仍在执行”。

---

## 12. 回滚设计

### 模式 B

优先顺序：

1. 若存在专用 `jenkins_rollback_job` -> 触发该 Job，参数带原 VERSION / BUILD；
2. 否则触发原 Job，参数 `ROLLBACK=1` + 历史 VERSION；
3. UI 文案：**重新执行 Jenkins 回滚/历史版本发布**，不承诺数据回滚。

### 模式 C

- 仅展示有完整 artifact 快照的成功记录；
- 新记录 `trigger_type=rollback`，策略只读快照；
- UI 文案：**重新部署历史产物**，不承诺 DB 迁移回滚。

---

## 13. 可观测与审计

每次发布至少审计：

- actor、IP、app、env、version
- release_mode、job、build_number
- 审批人/意见
- 终态与错误摘要

可选增强：

- 发布成功率、平均耗时进报表中心
- 失败一键转工单（带上 record 链接与 Jenkins URL）
- 与巡检/告警联动：发布窗口内的告警打标 `related_deploy_id`

---

## 14. 分期落地

### Phase 0 — 决策与盘点（0.5～1 天）

- [ ] 列出要接入的应用与对应 Jenkins Job
- [ ] 标注每个 Job：是否已包含部署、是否可加参数、是否能回调
- [ ] 确定首批只做模式 B 的应用名单
- [ ] 约定参数名与 Credentials（平台 API 用户）

### Phase 1 — 模式 B 主路径（推荐先上）

- [ ] 系统配置：Jenkins URL/Token/测试连接（已有则补强脱敏与 TLS）
- [ ] 新增 `release_mode=jenkins_governed` 分流：只触发 + 轮询/回调，不拉包不部署
- [ ] 修复构建号关联（queue -> build_number，失败不盲信 lastBuild）
- [ ] 发布详情展示 Jenkins 链接与结果
- [ ] app+env 串行锁 + 启动收敛僵尸任务
- [ ] prod 审批强制与审计字段补齐
- [ ] 文档：给用户的「从平台点发布」操作说明

**完成标准：**

- 从平台对 1～N 个现网 Job 完成 staging 发布；
- Jenkins 与平台终态一致；
- 平台重启后任务可收敛，不出现永久卡在 building。

### Phase 2 — 体验与治理增强

- [ ] Jenkins 控制台日志增量回传（progressiveText）或至少失败时拉取末尾日志
- [ ] 回调接口与幂等
- [ ] 回滚参数化 Job
- [ ] 失败转工单
- [ ] 应用级「测试 Job」按钮

### Phase 3 — 模式 C 试点（可选）

前置条件：

- [ ] 产物只认 record 快照 + sha256
- [ ] 指定版本链路与策略读取不一致问题已修
- [ ] 任务执行可靠性达标
- [ ] 选定 1 个非核心 SSH 应用；Jenkins Job 已去掉部署 stage

试点步骤：

1. Job 改为 `build_only` + archive
2. 平台 `jenkins_build_only` 仅对 dev 开放
3. 对比 2 周：成功率、耗时、回滚可用性、操作成本
4. 通过后再考虑 staging；prod 单独评审

### Phase 4 — 生产级（更长期）

- 任务队列化
- 多 Jenkins / 凭证分应用
- Docker/K8s 策略生产化（无停机切换、digest、失败 undo）
- 与现有深接入文档 `docs/design/jenkins-integration.md` 中仍有价值的部分合并归档

---

## 15. 与旧方案的关系

| 文档 | 立场 |
|------|------|
| `docs/design/jenkins-integration.md` | 平台触发 -> 拉产物 -> 平台部署（接近模式 C） |
| **本文** | **默认模式 B；模式 C 降级为有门槛的试点** |

处理建议：

1. 本文作为 **现行接入策略**；
2. 旧文档保留为「模式 C 实现参考」，文首增加过时说明，避免执行时按旧默认路径推全量；
3. 实现时若与旧文档冲突，**以本文为准**。

---

## 16. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 业务以为平台已部署，实际只是触发失败 | 误判发布成功 | UI 明确「以 Jenkins 结果为准」；无 build_number 不得标 success |
| Jenkins 手工又发了一版 | 平台记录缺失 | 流程上收紧 Job 权限；后续可做 Jenkins 审计同步（非必须） |
| 回调 token 泄漏 | 伪造终态 | 仅内网、可轮换、不写仓库 |
| 过早上模式 C | 发错包/停机 | 环境白名单 + 功能开关 + 试点评审 |
| 轮询压垮 Jenkins | API 压力 | 5s 间隔、指数退避、优先回调 |

---

## 17. 验收标准

### 模式 B

1. 管理员配置 Jenkins 后测试连接成功。
2. 用户对映射应用发起 staging 发布，Jenkins 出现对应参数化构建。
3. 平台记录展示正确 build number 与可点击 URL。
4. Jenkins 成功/失败时，平台 1 分钟内（或回调即时）收敛到一致终态。
5. prod 未审批不能触发 Job。
6. 无 `deploy.execute` 权限用户不能触发。
7. 平台重启后，进行中单子可收敛或明确失败，不永久悬挂。
8. 审计日志包含操作者、应用、环境、版本、Job、build number。

### 模式 C（若启动试点）

1. 构建产物 sha256 写入快照。
2. 策略执行只读快照路径，人工改环境当前产物不影响进行中/回滚单。
3. Jenkins Deploy stage 在 `build_only` 下不执行。
4. 仅白名单环境可创建该模式发布单。

---

## 18. 推荐默认决策（写给执行同学）

1. **现在就接 Jenkins，但接的是治理触发（模式 B），不是替换部署。**
2. **不要让现有 `build_mode=jenkins` 的“拉包+平台部署”成为现网默认。**
3. **先打通 1 条真实业务 Job 的参数契约与状态回传，再铺多个应用。**
4. **模式 C 只作为后续增强，且必须先修产物快照与任务可靠性。**
5. **任何阶段保留纯 Jenkins 操作能力作为应急回退。**

---

## 19. 附录

### 19.1 模式对照一句话

- **A**：平台只是书签
- **B**：平台是发布台，Jenkins 是施工队
- **C**：Jenkins 是包工队，平台是施工队
- **D**：平台自建施工队（暂不做）

### 19.2 首周实施清单（极简）

1. 定 1 个应用 + 1 个 staging Job
2. Job 增加参数：`APP_NAME ENV VERSION OPERATOR RECORD_ID RELEASE_MODE`
3. 平台配置 Jenkins，映射 Job
4. 实现/调整触发链路为模式 B
5. 跑通：平台点发布 -> Jenkins 执行 -> 平台显示成功
6. 补审批与审计演示给使用者

### 19.3 开放问题（实现前确认）

1. 现网 Job 是否已参数化？参数名是否可统一？
2. 是否允许平台 API 用户 `Job/Build` 与 `stop`？
3. 回调是内网 HTTP 还是必须 HTTPS？
4. 回滚是独立 Job 还是同 Job 参数？
5. 首批接入应用列表与负责人？

---

## 20. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-13 | 初稿：确立「浅接入默认、深接入试点」策略与契约 |
