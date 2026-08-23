# 模式 B（Jenkins 治理触发）链路验证 demo

验证目标：**不动现有 Jenkins job**，用一个 demo job 跑通
「平台触发 → Jenkins 执行 → 回调 → 平台状态更新」整条链路。

平台侧已提供三个端点（`backend/app/api/deploy_jenkins.py`）：

| 端点 | 用途 | 认证 |
|---|---|---|
| `GET /api/v1/deploy/jenkins/demo/config` | 拿回调地址 | JWT + `deploy.execute` |
| `POST /api/v1/deploy/jenkins/demo/trigger` | 触发 demo job，建 triggering 记录 | JWT + `deploy.execute` |
| `POST /api/v1/deploy/jenkins/callback` | Jenkins post 阶段回调 | `X-Deploy-Token` 头（**一次性 token**：触发时生成、随构建参数下发、用后即焚） |

---

## 操作步骤

### 1. 平台侧准备

- 系统设置里已配置 **Jenkins**（URL / 用户名 / API Token）——demo 复用这份配置
- 重启后端（加载新路由）

### 2. 拿回调地址

登录平台后，从浏览器 F12 → Application → Local Storage 拿 JWT（或用登录接口），
然后：

```bash
TOKEN="<你的JWT>"
curl -H "Authorization: Bearer $TOKEN" \
  http://<后端地址>:8000/api/v1/deploy/jenkins/demo/config
```

返回：

```json
{
  "code": 0,
  "data": {
    "callback_url": "http://<后端地址>:8000/api/v1/deploy/jenkins/callback",
    "demo_job_default": "ops-modeb-demo"
  }
}
```

> `callback_url` 是按请求地址推断的。**Jenkins 在 K8s 集群里时，改用集群内地址**，
> 如 `http://backend.ops-platform.svc:8000/api/v1/deploy/jenkins/callback`（按你的实际
> namespace/service 名改）。

### 3. Jenkins 建 demo job

1. Jenkins → 新建任务 → **Pipeline**，名称 `ops-modeb-demo`
2. 勾选「参数化构建」**不需要**——Jenkinsfile 里 `parameters` 块会自动声明
3. Pipeline → Definition: *Pipeline script*，粘贴本目录 `Jenkinsfile`
4. **只改一处**：`CALLBACK_URL` 改成步骤 2 拿到的地址（注意集群内/外网络）。
   **Jenkins 侧无需配置任何凭据**——回调 token 由平台每次触发时生成、随构建参数
   `CALLBACK_TOKEN` 自动下发、用后即焚。
5. **⚠️ 先手动空跑一次（Jenkins 经典坑）**：Declarative Pipeline 的 `parameters`
   块只在 job **运行过一次后**才注册为 job 参数。刚建的 job 直接被平台触发会
   `buildWithParameters → HTTP 500`（Jenkins 认为是无参数 job）。
   处理：左侧点 **Build Now** 空跑一次（这次会失败，参数为空，预期内），
   刷新后左侧出现 **Build with Parameters** 按钮即注册成功，再走步骤 4 触发。
   注意：**修改 Jenkinsfile 的 parameters 块后同样要空跑一次**让新参数注册。

### 4. 触发成功链路

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"env": "dev", "version": "demo-1", "simulate": "success"}' \
  http://<后端地址>:8000/api/v1/deploy/jenkins/demo/trigger
```

观察：

1. 平台「应用发布 → 部署记录」出现 **jenkins-modeb-demo** 应用的记录，
   状态 `triggering`（部署阶段 sleep 10s，有足够时间看到）
2. Jenkins job 执行：参数回显 → 构建(3s) → 部署(10s) → post 回调
3. 平台记录变为 `success`，日志里有 `[Jenkins 回调] status=success build_url=…`

### 5. 触发失败链路

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"env": "dev", "simulate": "failure"}' \
  http://<后端地址>:8000/api/v1/deploy/jenkins/demo/trigger
```

预期：Jenkins 部署 stage 抛错 → post failure 回调 → 平台记录变 `failed`，
`error_message` 带 Jenkins 提示。

### 6. 验证回滚分支（可选）

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"env": "dev", "release_mode": "rollback", "version": "demo-1"}' \
  http://<后端地址>:8000/api/v1/deploy/jenkins/demo/trigger
```

预期：跳过构建 stage，直接走回滚部署，平台记录 `trigger_type=rollback`。

### 7. 验证一次性 token（可选）

- 用已完成的记录 ID + 它当时的 token 重放回调 → token 已焚毁，被拒
  （或状态非 triggering → no-op，两者取先命中者）
- 用错误 token 回调 triggering 记录 → 拒绝，记录不受影响

一次性 token 在 Jenkins 构建参数 `CALLBACK_TOKEN` 里可见（构建进行中），
但只绑定当次记录、用后即焚，泄露无影响。

---

## 清理

测试完删除 demo 应用即可（级联删记录）：
应用发布 → 应用管理 → 找到 `jenkins-modeb-demo` → 删除。
（demo 应用是 `archived` 状态，不干扰正常列表。）

## 已知边界（demo 阶段故意不做）

- 无 triggering 超时对账（回调丢了记录会一直停在 triggering——正式版有定时对账兜底）
- 无并发锁（同时触发多条 demo 记录互不影响，但正式版必须加 app+env 互斥）
- `triggering` 状态在前端部署记录页显示为原始文本，无专属图标
- 取消按钮对 triggering 无效（正式版会联动 Jenkins stop API）
