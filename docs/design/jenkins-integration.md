# Jenkins 集成设计方案

> **状态说明（2026-07-13）**  
> 本文描述的是「平台触发 Jenkins 构建 → 拉取产物 → 平台执行部署」路径，对应新策略中的 **模式 C（构建分离 / 试点）**。  
> **现行默认接入策略已调整为模式 B（治理触发：平台审批/触发/审计，Jenkins 继续负责构建与现网部署）**。  
> 请优先阅读：`docs/superpowers/specs/2026-07-13-jenkins-release-integration-design.md`。  
> 若与该文档冲突，**以新文档为准**。本文仅作为模式 C 的实现参考保留。

## 1. 目标

平台作为唯一操作入口，用户无需访问 Jenkins 页面。平台负责触发构建、监控进度、拉取产物、执行部署，Jenkins 仅承担代码编译打包。

> 注意：上述目标对应模式 C。现网若 Jenkins 已包含部署步骤，不应直接按本文全量落地，而应先走模式 B。

## 2. 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    运维平台                           │
│                                                     │
│  用户点"部署"                                        │
│      ↓                                              │
│  ① 触发 Jenkins Job  ──→  Jenkins Server            │
│      ↓                         │                    │
│  ② 轮询构建状态     ←──  构建进度/结果               │
│      ↓                         │                    │
│  ③ 拉取产物         ←──  archiveArtifacts           │
│      ↓                                              │
│  ④ SSH 上传到目标服务器                               │
│      ↓                                              │
│  ⑤ 执行部署脚本                                      │
│      ↓                                              │
│  ⑥ 健康检查                                          │
│      ↓                                              │
│  ⑦ 成功/失败 → 记录 + 回滚能力                       │
└─────────────────────────────────────────────────────┘
```

## 3. Jenkins 配置管理

### 3.1 数据结构

`system_configs` 表中 `key = "jenkins_config"`，`value` 为 JSON：

```json
{
  "url": "http://jenkins.example.com:8080",
  "username": "admin",
  "token": "xxxxxxxxxxxxxxxx"
}
```

### 3.2 后端

在 `backend/app/api/settings.py` 的 `_CONFIG_SPECS` 中新增：

```python
"jenkins.url": "Jenkins 服务地址（例：http://jenkins.example.com:8080）",
"jenkins.username": "Jenkins 用户名",
"jenkins.token": "Jenkins API Token",
```

新增连接测试接口 `POST /api/v1/settings/jenkins/test-connection`：
- 调用 Jenkins `/api/json` 验证连通性和凭据
- 返回 Jenkins 版本信息

### 3.3 前端

设置页新增"Jenkins 配置"卡片：
- URL 输入框
- 用户名输入框
- API Token 输入框（密码类型）
- "测试连接"按钮
- 连接成功后显示 Jenkins 版本

## 4. 构建流程改造

### 4.1 现有流程（保留）

`builder.py` 中 `_build_jenkins()` 已实现：
- ✅ 触发构建（`/job/{name}/build` 或 `/buildWithParameters`）
- ✅ 等待队列分配（轮询 queue API）
- ✅ 轮询构建状态（进度百分比）

### 4.2 新增：产物拉取

构建成功后，从 Jenkins 下载归档产物。

**Jenkins API**：
```
GET /job/{jobName}/{buildNumber}/artifact/{relativePath}
```

**实现逻辑**（`builder.py` `_build_jenkins()` 末尾）：

```python
# 构建成功后拉取产物
if result == "SUCCESS":
    artifact_path = _fetch_jenkins_artifact(base_url, auth, job_name, build_number, app)
    if artifact_path:
        return artifact_path
    else:
        append_log(db, record, "Jenkins 构建成功但未找到归档产物，请确认 Job 配置了 archiveArtifacts")
        return None
```

**`_fetch_jenkins_artifact()` 流程**：
1. 调用 `/job/{name}/{buildNumber}/api/json` 获取 `artifacts` 列表
2. 遍历 artifacts，匹配文件名模式（优先 `.jar`，其次 `.war`，最后取第一个）
3. 下载到本地 `DEPLOY_ARTIFACT_DIR/{app_name}/jenkins/` 目录
4. 文件名格式：`{buildNumber}_{originalFilename}`（如 `42_smart-subItem.jar`）
5. 返回本地文件路径

**产物路径更新**：
- 下载成功后，更新 `app_env.artifact_path`、`artifact_filename`、`artifact_size`、`artifact_uploaded_at`
- 这样回滚时能正确找到 Jenkins 构建的产物

### 4.3 新增：构建日志回传

在轮询构建状态的同时，增量拉取 Jenkins 控制台输出。

**Jenkins API**：
```
GET /job/{jobName}/{buildNumber}/logText/progressiveText?start=0
```

**实现**：
- `_poll_build_status()` 中增加 `start_offset` 参数
- 每次轮询时调用 `progressiveText` 获取新增日志
- 通过 `append_log()` 写入部署记录
- 用户在平台上能看到完整的构建过程

### 4.4 配置快照更新

`records.py` 中 `execute_deploy()` 的配置快照增加 Jenkins 构建号：

```python
config_snapshot = json.dumps({
    ...
    "jenkins_build_number": build_number,  # 新增
    "artifact_path": artifact_path,
    "artifact_filename": artifact_filename,
})
```

回滚时可通过构建号精确定位产物。

## 5. Jenkins Job 规范

### 5.1 推荐的 Jenkinsfile 模板

```groovy
pipeline {
    agent { label 'build-agent' }

    environment {
        // 构建参数
    }

    stages {
        stage('拉取代码') {
            steps {
                checkout scm  // 或指定 GitSCM
            }
        }

        stage('编译打包') {
            steps {
                sh 'mvn -U clean package -Dmaven.test.skip=true'
            }
        }
    }

    post {
        success {
            // 归档产物，平台通过 API 拉取
            archiveArtifacts artifacts: '**/target/*.jar', fingerprint: true
        }
    }
}
```

### 5.2 关键要求

| 要求 | 说明 |
|------|------|
| 必须有 `archiveArtifacts` | 平台通过此 API 拉取产物 |
| 去掉 SCP/SSH 部署步骤 | 部署由平台 SSH 策略负责 |
| 去掉健康检查步骤 | 由平台负责 |
| 去掉备份步骤 | 平台通过时间戳文件名 + 软链接管理版本 |

### 5.3 参数化构建（可选）

如果 Job 需要参数（如分支名、环境），可在平台应用配置中定义 Jenkins 参数，触发时传递：

```
POST /job/{name}/buildWithParameters
Body: branch=production&env=staging
```

## 6. 前端改动

### 6.1 设置页

新增 Jenkins 配置区域，与 Prometheus/Alertmanager/LLM 同级。

### 6.2 应用创建/编辑页

现有 Jenkins 相关字段保留（Job 名称、Token）。新增：
- "测试 Job" 按钮：验证 Job 是否存在且可触发

### 6.3 应用详情页

构建模式为 Jenkins 时：
- 概览 Tab：显示最近一次 Jenkins 构建号和状态
- 环境 Tab：显示"上次构建产物"（来自 Jenkins 归档）
- 部署历史 Tab：显示 Jenkins 构建号

### 6.4 部署弹窗

Jenkins 模式下新增：
- 可选参数输入（如果 Job 有参数化配置）
- 提示"将触发 Jenkins 构建，完成后自动部署"

## 7. 错误处理

| 场景 | 处理 |
|------|------|
| Jenkins 未配置 | 阻止部署，提示"请先在系统设置中配置 Jenkins" |
| Jenkins 不可达 | 阻止部署，返回连接错误 |
| Job 不存在 | 阻止部署，提示"Job {name} 不存在" |
| 构建触发失败 | 记录失败，返回 HTTP 状态码 |
| 构建超时（>10min） | 标记失败，记录超时 |
| 构建失败 | 标记失败，回传 Jenkins 控制台日志 |
| 构建成功但无归档产物 | 标记失败，提示"请确认 Job 配置了 archiveArtifacts" |
| 产物下载失败 | 标记失败，记录错误 |
| 部署阶段失败 | 走现有的回滚逻辑 |

## 8. 实现分期

### 第一期：基础集成

1. 设置页 Jenkins 配置 + 连接测试
2. 构建成功后从 Jenkins 拉取产物
3. 更新配置快照（含构建号）
4. 前端部署弹窗适配

### 第二期：体验优化

1. 构建日志实时回传（consoleText）
2. Jenkins Job 参数化支持
3. 应用详情页 Jenkins 构建信息展示
4. "测试 Job" 按钮

### 第三期：高级功能

1. 多 Jenkins 服务器支持（不同 Job 可配不同 Jenkins）
2. Jenkins 构建触发 Webhook（实时通知构建结果，替代轮询）
3. Jenkins Blue Ocean 链接跳转

## 9. 技术要点

- **产物下载**：Jenkins 归档产物通过 `/artifact/` API 下载，需要 Basic Auth
- **大文件**：产物可能较大（100MB+），下载时用 `httpx` 流式写入，记录进度
- **产物命名**：用 `{buildNumber}_{originalFilename}` 避免覆盖，与现有时间戳命名风格一致
- **兼容性**：现有 `upload` 模式不受影响，Jenkins 模式是独立的 `build_mode`
- **回滚**：Jenkins 构建的产物下载到本地后，回滚逻辑与文件上传模式完全一致
