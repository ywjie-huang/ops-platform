# 运维管理平台全面评估报告

> 评估日期：2026-07-10
> 评估对象：`D:\my-project`
> 评估范围：UI/UX、前后端架构、代码质量、功能实现、安全性、可靠性、测试、构建、部署和生产可维护性
> 评估方式：源码静态审计、登录页运行时检查、测试与构建验证、受保护 API 只读冒烟验证
> 说明：本轮评估未修改业务代码，未执行业务写操作。

---

## 1. 管理层结论

**综合成熟度：48 / 100**

一句话评价：

> 这是一个功能覆盖较广、产品骨架比较完整的运维管理平台，监控、资产、告警、容器、SSH、巡检、工单、AI、应用发布等模块均已有真实业务实现；但目前存在多条可直接控制远程主机、读取敏感凭据或绕过权限的高危链路，安全基线严重不足，因此当前更适合作为隔离网络中的内测/PoC 系统，不建议直接部署到企业生产环境。

### 1.1 上线判断

| 场景 | 建议 |
|---|---|
| 本地开发 | 可以 |
| 隔离测试环境 | 可以，但应严格限制网络访问 |
| 企业内部测试 | 修复 P0 后再开放 |
| 连接真实生产主机 | **当前不建议** |
| 公网部署 | **禁止** |
| 正式生产上线 | **暂不具备条件** |

---

## 2. 量化评分

| 评估维度 | 分数 | 评价 |
|---|---:|---|
| 产品与功能覆盖 | **76** | 核心模块较齐全，多数已有真实业务链路 |
| 架构设计 | **62** | 前后端分层清楚，但任务调度、迁移和后台执行方式不够生产化 |
| 后端代码质量 | **55** | 基本规范，但存在巨型模块、宽泛异常和职责过重 |
| 前端代码质量 | **48** | 功能可以落地，但大组件、`any`、类型错误和风格分裂明显 |
| UI/UX | **61** | 登录页完成度不错，但全局视觉语言、移动端体验不统一 |
| 可访问性与响应式 | **53** | 有部分语义化基础，但键盘操作、ARIA、移动导航仍不完整 |
| 测试与质量门禁 | **46** | 有一定测试数量，但缺少有效 E2E，正式前端构建目前失败 |
| DevOps/生产可运维性 | **38** | 缺少可靠任务队列、持久调度、健康检查和安全镜像基线 |
| 安全性 | **12** | 存在已验证的身份伪造、未认证 SSH/SFTP/命令执行等问题 |

---

## 3. 必须立即处理的 P0 问题

这些问题不是普通代码规范问题，而是可能直接导致服务器接管、凭据泄漏和远程命令执行的问题。

### P0-1：JWT 使用仓库内固定密钥，管理员身份可以被伪造

位置：

`D:\my-project\backend\app\core\config.py:25`

```python
SECRET_KEY: Final = "dev-secret-key-change-me"
```

审计中已做只读验证：使用仓库里的固定密钥在本地生成管理员身份 JWT 后，可以成功访问当前用户、Dashboard、资产、巡检、工单、部署、AI、报表、调度任务等受保护接口。验证过程中没有执行写操作，本报告也不会公开生成的令牌。

#### 风险

只要攻击者拿到源码、镜像、历史提交或默认配置，就可能自行签发管理员令牌，整个 RBAC 体系随之失效。

同时还存在默认凭据或高风险默认配置：

- 数据库：`root / 123456`
- 系统管理员：`admin / admin123`
- Docker Compose 直接暴露 MySQL 3306
- 数据库使用 root 用户

#### 处理要求

1. JWT Secret 必须通过环境变量或密钥管理系统注入。
2. 缺少 Secret 时应用必须拒绝启动，不能回退到默认值。
3. 立即轮换现有 Secret，使已有伪造或泄漏 Token 全部失效。
4. 默认管理员首次登录强制修改密码。
5. 生产环境禁止内置固定密码。
6. 后续增加 Token 撤销、短期 Access Token 和 Refresh Token 轮换。

### P0-2：SSH Key 管理接口没有认证，且可能明文返回秘密

位置：

`D:\my-project\backend\app\api\ssh_keys.py:83-186`

SSH Key CRUD 接口缺少当前用户认证和权限依赖，详情返回模型中包含：

- 密码
- 私钥
- 私钥口令

相关秘密还采用明文存储。

#### 风险

未登录用户可能读取平台保存的远程主机密码或私钥，继而绕过平台直接登录服务器。

#### 处理要求

- 所有接口增加 JWT 认证。
- 分别设置 `ssh_keys.read/create/update/delete` 权限。
- 列表和详情接口永远不返回密码、私钥、passphrase 原文。
- 数据库中使用字段级加密。
- 审计日志仅记录“修改了凭据”，禁止记录秘密内容。
- 私钥下载默认禁止；确有需求时需要二次认证和完整审计。

### P0-3：SFTP 接口整体缺少认证

位置：

`D:\my-project\backend\app\api\sftp.py:63-340`

文件列表、读取、写入、上传、下载、创建目录、删除、重命名和文件状态查询等操作没有形成有效的登录和权限闭环。

#### 风险

攻击者可能直接使用系统保存的资产凭据，对远程服务器文件进行读取、覆盖或删除。

#### 处理要求

至少划分以下权限：

- `sftp.read`
- `sftp.upload`
- `sftp.write`
- `sftp.delete`

并增加路径白名单、上传大小限制、扩展名策略、敏感目录限制，以及用户、资产、源 IP、路径和文件哈希审计。

### P0-4：SSH Terminal WebSocket 缺少 JWT 和 RBAC

位置：

`D:\my-project\backend\app\api\ssh_terminal.py:46-90`

WebSocket 建立后直接接收认证数据并连接资产，未形成可靠的用户鉴权，审计用户还是空值。

#### 风险

攻击者可能绕过后台登录和权限体系，直接建立远程主机终端。

#### 处理要求

- WebSocket 握手阶段验证短期 JWT。
- 校验 `ssh.terminal.connect` 权限。
- 校验用户是否有权操作指定资产。
- 禁止前端传入任意用户名、密码覆盖平台策略。
- 记录用户、资产、连接时间、断开时间和会话 ID。
- 对终端输入输出进行合规审计或命令审计。
- 增加并发、空闲超时和会话时长限制。

### P0-5：批量执行 WebSocket 未认证，可执行任意命令

位置：

`D:\my-project\backend\app\api\batch_exec.py:67-145`

接口直接接收 `asset_ids`、任意 `command` 和 `timeout`，然后读取资产保存的 SSH 凭据执行命令，操作人信息为空。

#### 风险

这是直接的远程命令执行入口。若网络可访问，攻击者可能批量控制所有已纳管主机。

#### 处理要求

- 修复前暂时关闭该接口。
- 增加登录、`batch_exec.execute` 权限和资产范围权限。
- 操作必须绑定当前用户。
- 增加高风险命令拦截与二次确认。
- 对删除、关机、用户管理、防火墙操作等设置审批策略。
- 保存命令、目标、输出、退出码、时间和操作人审计。
- 限制批量目标数量、执行超时和输出大小。

### P0-6：Docker Agent 相当于裸露的 Docker Root API

位置：

`D:\my-project\agent\docker_agent.py:246-373`

当前 Agent：

- 没有 Token
- 没有 mTLS
- 没有 IP 白名单
- CORS 为 `*`
- 支持容器 start/stop/restart/delete
- 删除使用 `force=True`
- 监听 `0.0.0.0:9001`
- 挂载 Docker Socket
- Compose 映射 `9001:9001`

#### 风险

能够调用 Agent 的人，基本相当于获得宿主机 Docker 管理权限。Docker Socket 本身通常等价于宿主机 root 级能力。

#### 处理要求

1. 立即停止对外映射 9001。
2. Agent 仅监听管理网卡或 `127.0.0.1`。
3. 后端与 Agent 之间使用 mTLS。
4. 增加短期签名 Token、时间戳和 nonce，防止重放。
5. 配置来源 IP 白名单。
6. 去掉 CORS `*`。
7. 默认关闭强制删除。
8. Agent 操作全部记录操作人和请求来源。
9. 从网络层确保 Agent 只能被后端访问。

### P0-7：部署 Webhook 可能形成未认证任意文件写

相关位置：

- `D:\my-project\backend\app\api\deploy.py:1363-1452`
- `D:\my-project\backend\app\services\deploy\webhook.py:22-153`

主要问题：

- Webhook Secret 为空时会跳过签名验证。
- Build Number、上传文件名、URL 文件名未充分净化。
- 直接使用 `os.path.join()` 拼接路径。
- 存在路径穿越风险。
- 上传、下载缺少大小限制。
- URL 下载目标不受限制。
- TLS 使用 `verify=False`。
- URL 下载可能形成 SSRF。

#### 风险

攻击者可能让服务端下载恶意内容，访问内网地址，或将文件写入预期目录之外。

#### 处理要求

- Webhook Secret 必填，缺少时拒绝启动或禁用接口。
- 使用 HMAC 签名，并校验时间戳和重放。
- 使用 canonical path 校验最终路径必须位于产物目录内。
- 文件名只允许安全字符，拒绝路径分隔符。
- 限制上传和下载大小。
- 限制允许下载的域名、协议和端口。
- 禁止访问回环、链路本地地址、内网网段和云元数据地址。
- 恢复 TLS 证书校验。

---

## 4. 重要 P1 问题

### 4.1 AI 会话存在越权访问和工具权限绕过

相关位置：

- `D:\my-project\backend\app\api\ai.py`
- `D:\my-project\backend\app\services\ai\conversations.py`

问题包括：

- 获取消息、删除会话、继续会话仅按 `conversation_id` 查询。
- 没有充分检查会话所属用户。
- AI 接口主要只要求登录，没有对应 AI 权限。
- AI 工具可以触发 SSH 命令、巡检、创建工单。
- 工具执行没有再次检查对应业务权限。
- 可能绕过 `batch_exec.execute`、`patrol.execute`、`tickets.create`。
- Pending Action 使用全局内存字典，未可靠绑定用户且缺少 TTL。
- 多进程部署时 Pending Action 状态不共享。
- Confirm 请求中的 conversation ID 校验不足。
- 仅配置 SSH Key 的资产，连接测试与真正执行命令的认证参数存在不一致。

#### 建议

- 所有会话查询必须同时带 `conversation_id + user_id`。
- AI 路由增加 `ai.access` 等权限。
- 每一个工具单独声明和校验业务权限。
- 写工具确认记录绑定用户、会话、动作、参数哈希和过期时间。
- 确认 Token 单次使用。
- Pending Action 存入 Redis 或数据库。
- AI 不能成为绕过原业务 API 权限的“超级入口”。

### 4.2 系统配置可能泄漏 API Key 和 Token

位置：

`D:\my-project\backend\app\api\settings.py:226-278`

当前系统配置列表、详情和更新审计可能原样处理配置值，包括 LLM API Key、Jenkins Token 和其他外部系统密码。

#### 建议

- 后端根据配置类型统一脱敏。
- API 只返回 `configured: true/false` 或掩码。
- 更新时空值表示“不修改”，而不是要求前端回传旧值。
- 审计日志禁止记录新旧秘密原文。
- 数据库存储使用加密字段或专用 Secret Manager。

### 4.3 回滚链路可能绕过部署审批

位置：

`D:\my-project\backend\app\api\deploy.py:702-794`

普通部署会检查 `approval_required`，但回滚路径没有执行同等审批，直接启动后台线程。

部署和回滚应该使用统一状态机：

```text
草稿 → 待审批 → 已批准 → 执行中 → 成功/失败/已取消
```

回滚不应因为名称是“回滚”就天然绕过审批；生产环境回滚同样是高风险变更。

### 4.4 “部署指定构建版本”存在链路不一致

涉及：

- `D:\my-project\backend\app\api\deploy.py:1232-1294`
- `D:\my-project\backend\app\services\deploy\records.py:171-259`
- `D:\my-project\backend\app\services\deploy\builder.py:48-52`
- `D:\my-project\backend\app\services\deploy\strategies\ssh_strategy.py:81`

API 虽然将用户选中的构建产物写入 Snapshot，但后续 SSH Strategy 仍可能从环境当前的 `artifact_path` 读取。

实际风险是：用户选择构建版本 A，最终部署的却可能是环境当前产物 B，页面显示、记录和实际执行结果可能不一致。

建议部署任务创建时生成不可变 Deployment Snapshot，包含 artifact ID、artifact path、SHA-256、build number、image digest、commit SHA 和执行参数。所有 Strategy 只能读取 Snapshot，禁止运行过程中重新读取当前配置。

### 4.5 前端路由守卫没有真正检查 permission

位置：

`D:\my-project\frontend\src\router\index.ts:18-50`

路由守卫只检查 Token 和用户信息，没有对 `to.meta.permission` 调用 `authStore.hasPermission()`。菜单隐藏不等于权限控制，用户仍可直接输入 URL 访问页面，AI 路由本身也缺少明确权限。

虽然真正的数据安全必须由后端保障，但前端也应形成完整体验：

- 菜单权限
- 路由权限
- 按钮权限
- 后端 API 权限
- 数据范围权限

### 4.6 其他重要安全问题

- `D:\my-project\backend\app\api\ssh_common.py:74` 使用 `paramiko.AutoAddPolicy()`，没有可靠验证主机指纹。
- 多处 TLS 请求使用 `verify=False`。
- 系统配置连接测试可能形成 SSRF。
- JWT 存储在 localStorage，生命周期约 12 小时，缺少撤销与轮换。
- 缺少登录限流和账号锁定。
- Alertmanager Webhook 缺少签名或来源校验。
- 无条件信任 `X-Forwarded-For`。
- CORS `*` 与 Credentials 配置组合风险较高。
- Nginx 缺少 CSP、HSTS、X-Frame-Options、nosniff 等安全响应头。
- 容器默认以 root 身份运行。

---

## 5. 功能实现完整度

### 5.1 完成度较高的模块

| 模块 | 评价 |
|---|---|
| Dashboard | 有实际统计和状态展示 |
| 资产管理 | 资产、凭据、详情、监控链路较完整 |
| Prometheus 监控 | 已有真实指标查询 |
| Alertmanager | 包含状态、规则、告警和 Webhook |
| Kubernetes | 有发现、日志、事件、删除和重启能力 |
| Docker | 有主机、容器监控和生命周期操作 |
| SSH Terminal | 功能链路存在，但安全认证严重不足 |
| SFTP | 功能较全，但当前权限闭环缺失 |
| 批量执行 | 已实现真实命令执行，但属于高危入口 |
| 巡检 | 报告和任务链路已有真实数据 |
| 用户/角色/RBAC | 框架较完整，但存在若干绕过路径 |
| 工单 | 已有基本业务闭环 |
| AI 助手 | 已有流式输出、工具调用、确认/拒绝 |
| 应用发布 | 应用、环境、构建、审批、回滚、记录框架较完整 |

### 5.2 部分实现或仍为预留的功能

- 资产详情中的工单关联、变更记录仍有预留文案。
- Header 命令面板存在 TODO。
- SSH 文件预览仍是预留能力。
- Scheduler 当前主要支持巡检，`report` 和 `backup` 仍为预留类型。
- 报表模块主要是预置报表和即时查询，不是完整的持久化报表 CRUD。
- Seed 中存在 `reports.create/update/delete` 权限，但后端没有完整对应实现。
- 指定构建、审批、任务恢复等发布链路还未完全闭环。

因此需要明确：页面和接口存在，不等于生产级闭环已经完成。

---

## 6. UI/UX 评估

### 6.1 优点

登录页面在实际运行时检查中表现不错：

- 1280×720、768×900、390×844 下没有横向溢出。
- 没有发现浏览器 Console 错误。
- 输入框具有比较明显的焦点环。
- 登录按钮约 46px，验证码按钮约 44px，触控尺寸基本合理。
- 已有 `main`、`form`、标题、标签等语义结构。
- 整体视觉完成度明显高于普通后台模板。

说明：本次浏览器运行时视觉检查集中在登录页；内页主要采用源码审计和受保护 API 只读冒烟验证，不能表述为所有内页均完成浏览器视觉验收。

### 6.2 全局视觉语言不统一

目前能看到多套风格：

- 登录页：深绿色赛博指挥台风格
- 主应用：浅色、偏 Linear 风格
- AI 页面：较明显的 Element Plus 默认视觉
- 巡检页面：单独的 cockpit 风格

单看某一个页面不一定差，但放在同一个产品中会显得像多个系统拼接。

建议建立统一的色彩、字体、圆角、阴影、间距、状态色、表格密度、空状态、错误状态、Loading/Skeleton，以及页面标题和操作区布局规范。

### 6.3 登录页移动端内容过长

在 390px 宽度下，页面总高度约 1920px。复杂的“运维态势预览”仍完整堆叠在登录表单之后。

建议在小屏幕下：

- 隐藏或折叠态势预览。
- 保留 Logo、标题、登录表单和必要说明。
- 将次要内容放入可展开区域。
- 优先保证登录表单位于首屏。

### 6.4 移动端侧边栏方案不完整

全局样式在约 860px 以下将 Sidebar 宽度设为 0，但点击 Header Toggle 后主要变为 48px 的折叠图标栏，并不是真正的移动端 Drawer。

建议改为带遮罩的移动端 Drawer，支持 Escape 关闭、菜单点击后自动关闭、焦点陷阱和焦点回归，并显示完整菜单名称。

### 6.5 AI 页面响应式和可访问性不足

位置：

`D:\my-project\frontend\src\views\ai\AiView.vue`

该页面约 995 行，存在固定 220px 侧栏、缺少明显移动端媒体查询、缺少 ARIA、缺少 reduced-motion 处理、Quick Question 使用可点击 `div` 等问题。

建议移动端将对话列表改为 Drawer，并把所有交互元素改成原生 `button`。

### 6.6 可访问性问题

典型问题包括：

- Header Toggle 使用 `div + @click`。
- Sidebar Collapse 使用 `div + @click`。
- 部署环境卡片 Header 使用点击 `div`。
- 部分交互元素缺少 `tabindex`。
- 缺少 `aria-expanded`、`aria-controls`、`aria-label`。
- 动画没有全面适配 `prefers-reduced-motion`。
- `D:\my-project\frontend\index.html:2` 使用 `<html lang="en">`，但主要界面是中文。

应改为：

```html
<html lang="zh-CN">
```

交互控件应优先使用原生 `<button type="button">`，而不是给 `div` 人工模拟按钮。

---

## 7. 前端代码质量

### 7.1 巨型组件较多

当前明显的大文件包括：

- `D:\my-project\frontend\src\views\deploy\AppDetailView.vue`：约 2073 行
- `D:\my-project\frontend\src\views\dashboard\DashboardView.vue`：约 1790 行
- `D:\my-project\frontend\src\views\settings\ModelConfigView.vue`：约 1328 行
- `D:\my-project\frontend\src\views\login\LoginView.vue`：约 1311 行
- 约 12 个 Vue SFC 超过 800 行

这些组件通常同时承担数据请求、状态管理、表单定义、业务判断、页面布局、弹窗、子流程和大量样式，长期会导致修改风险和回归成本快速增加。

以发布详情为例，建议拆分为：

```text
AppDetailView
├── AppOverviewPanel
├── EnvironmentMatrix
├── DeployDialog
├── BuildSelector
├── ApprovalPanel
├── RecordTable
├── DeployLogViewer
├── RollbackDialog
├── useDeployApplication
├── useDeployRecords
└── useDeploymentActions
```

### 7.2 类型安全不足

前端约有 336 处 `any`，明显削弱了 TypeScript 的价值。

建议：

- 根据后端响应创建统一 DTO。
- Axios 返回值使用泛型。
- 表单模型和状态枚举使用明确类型。
- 禁止新增无说明的 `any`。
- 为 WebSocket 消息定义 discriminated union。

### 7.3 设计规范落地不完整

审计中发现：

- 约 68 行静态 inline style。
- 约 390 行硬编码十六进制颜色。
- `.table-wrapper` 覆盖明显少于实际表格数量。
- 全局 Token 主要只有基础颜色。
- 缺少 spacing、type、shadow、focus、layer 等 Token。
- 全局断点使用 860px，与项目约定的 768px 不一致。
- 报表默认图标仍使用 Emoji。

建议扩展设计 Token：

```scss
--space-1;
--space-2;
--font-size-sm;
--font-size-md;
--radius-sm;
--radius-md;
--shadow-sm;
--focus-ring;
--layer-header;
--layer-drawer;
--duration-fast;
```

---

## 8. 后端架构和代码质量

### 8.1 正向评价

后端已经具备一定架构意识：

- API、Service、Model 三层基本清楚。
- 大多数 REST API 使用 FastAPI Depends。
- RBAC 已有统一权限依赖。
- SQLAlchemy 2 风格整体较现代。
- 外部请求普遍有 Timeout 意识。
- Prometheus、Alertmanager、Kubernetes、Docker、AI、部署均有独立服务层。
- 应用发布已经抽象出 Jenkins、SSH、Docker、K8s 等策略骨架。
- 时区处理有统一约定。

这些说明系统具备继续工程化的基础，不需要推倒重写。

### 8.2 巨型后端模块

- `D:\my-project\backend\app\api\deploy.py`：约 1910 行
- `D:\my-project\backend\app\db\init_db.py`：约 677 行

`deploy.py` 同时承担应用、环境、记录、审批、构建、Webhook、回滚等职责，建议按资源拆分路由和服务。

### 8.3 没有真正使用数据库迁移体系

项目依赖中已有 Alembic，但没有标准 migration 目录，主要依赖启动时的手写 `ALTER TABLE`。

风险包括：

- 迁移顺序难管理。
- 失败后恢复困难。
- 多实例同时启动可能冲突。
- 缺少可审计的升级和回滚版本。
- 应用启动和数据库升级强耦合。

建议迁移到 Alembic，并将数据库升级作为独立发布步骤。

### 8.4 后台任务机制不可靠

当前存在：

- APScheduler 内存 JobStore。
- 每个 Worker 都可能启动 Scheduler。
- 每个 Worker 都可能启动 Docker Polling。
- Docker Polling 使用 `while True`，缺少明确停止事件。
- 部署使用 daemon thread。
- 取消状态放在进程内字典。
- 多 Worker 之间状态不共享。

风险包括任务重复执行、进程重启后状态丢失、执行被中断、取消无法生效、缺少可靠重试和幂等。

建议引入 Redis + Celery/RQ/Dramatiq 等可靠队列，并配置独立 Worker、重试策略、幂等键、任务超时、分布式锁、持久化状态和 Graceful Shutdown。

### 8.5 异常捕获过宽

代码中约有 80 处较宽泛的：

```python
except Exception:
```

很多地方会模糊参数错误、网络错误、权限错误、业务冲突和系统异常。建议定义统一业务异常，并由全局 Handler 转换为统一响应。

### 8.6 健康检查过于简单

当前 `/health` 主要只返回：

```json
{"status": "ok"}
```

建议拆分：

- `/health/live`：进程是否存活。
- `/health/ready`：数据库、必要配置是否就绪。
- `/health/detail`：仅供内部监控，检查 Redis、调度器、任务队列等依赖。

---

## 9. 测试、构建和质量门禁

### 9.1 后端测试

按照项目文档中的标准命令执行：

```powershell
cd backend
python -m pytest -p no:cacheprovider -q
```

会失败：

```text
ModuleNotFoundError: No module named 'agent'
```

修正 Python Path 后结果为：

```text
43 passed, 2 warnings
```

说明测试本身多数可以通过，但仓库标准命令和真实执行环境不一致，开发者按文档操作会失败。两条 Warning 主要来自 SSH Key 的 Pydantic v2 旧式 Config。

### 9.2 前端测试

执行 Node 测试结果：

```text
85 passed
```

但测试主要是 Node Unit Test、源码/标记断言和部分静态行为检查，目前缺少足够的 Vue Test Utils 组件测试、路由权限测试、API Mock 集成测试、Playwright/Cypress E2E、WebSocket 测试，以及部署、审批和回滚业务测试。

### 9.3 正式前端构建失败

标准命令：

```powershell
npm run build
```

失败，共有约 12 个 TypeScript 错误，涉及：

- BatchExecView
- ApprovalView
- RoleListView
- SchedulerView

单独执行：

```powershell
npx vite build
```

可以通过，但这绕过了 TypeScript 检查。

`D:\my-project\frontend\Dockerfile:11` 当前使用：

```dockerfile
RUN npx vite build
```

因此当前 Docker 镜像可以构建，不代表正式前端质量门禁通过。建议 Dockerfile 执行标准构建，并让类型错误直接阻断 CI。

### 9.4 受保护 API 只读冒烟验证

以下接口类别在审计时均返回成功响应：

- Dashboard 统计
- 资产列表
- Alertmanager 状态
- Docker Overview
- 巡检报告
- 工单
- 发布应用
- AI 信息
- 报表 Preset
- Scheduler 任务

环境中已有真实数据，包括资产、巡检报告、工单、发布应用和预置报表。这说明多个业务模块并非纯静态页面，但不能替代写链路、异常链路和完整 E2E 验收。

---

## 10. DevOps 与生产可运维性

目前需要重点补齐：

- 可靠后台任务队列。
- 调度器持久化和 Leader Election。
- 数据库迁移版本管理。
- Readiness/Liveness Probe。
- 非 root 容器运行。
- 镜像依赖和基础镜像使用不可变版本或 Digest。
- Secret Manager 或字段级加密。
- 安全响应头。
- 数据备份、恢复和演练。
- 指标、日志、Trace 和审计日志关联。
- 发布任务恢复、幂等、重试和可靠取消。

---

## 11. 推荐整改路线

### 11.1 第一阶段：48 小时内止血

目标是避免系统被直接接管。

1. 暂时关闭或网络隔离：
   - SSH Terminal WebSocket
   - SFTP
   - Batch Exec WebSocket
   - SSH Key CRUD
   - Docker Agent 9001
   - 未签名部署 Webhook
2. 轮换 JWT Secret。
3. 清理固定默认密码。
4. 所有远程操作补 JWT、权限和当前用户审计。
5. Secret API 全面脱敏。
6. 禁止审计日志记录 API Key、密码和私钥。
7. Webhook 强制签名，修复路径穿越、SSRF 和无限上传。
8. Docker Agent 取消公网或普通局域网暴露。

#### 阶段验收标准

- 未登录请求不能连接任何远程主机。
- 未登录请求不能读取任何凭据。
- 普通用户不能通过 AI 或直接 URL 绕过权限。
- 仓库源码中的任何默认值不能用于签发有效生产 Token。

### 11.2 第二阶段：两周内稳定化

1. 修复全部 TypeScript 错误，使 `npm run build` 通过。
2. Dockerfile 使用正式构建命令。
3. 前端 Router Guard 校验 `meta.permission`。
4. AI 会话增加 Owner Check。
5. AI 工具增加工具级权限。
6. Pending Action 绑定用户并增加 TTL。
7. 回滚进入统一审批状态机。
8. 修复指定构建产物链路。
9. 引入 Alembic。
10. 后台部署迁移到可靠任务队列。
11. 增加登录限流。
12. 配置可信代理列表。
13. SSH 改用 known_hosts。
14. 建立 CI：Ruff/Black、MyPy、Pytest、ESLint、Type Check、Frontend Test、Production Build、Dependency Scan、Secret Scan。

### 11.3 第三阶段：1～2 个月工程化

1. Redis + 独立任务 Worker。
2. Scheduler 持久化和 Leader Election。
3. 部署任务幂等、恢复和可靠取消。
4. Vault/KMS 或字段加密。
5. 完整密钥轮换机制。
6. Vue Test Utils 组件测试。
7. Playwright 核心业务 E2E。
8. 安全回归测试：未认证访问、IDOR、权限绕过、SSRF、路径穿越、WebSocket 认证。
9. 拆分巨型 Vue SFC。
10. 拆分部署 API。
11. 统一设计系统和移动端 Drawer。
12. 非 root 容器、Readiness/Liveness。
13. 数据库备份恢复演练。
14. 镜像和依赖使用不可变版本。

---

## 12. 建议建立的上线质量门禁

只有以下门禁全部通过，才建议进入正式生产评审：

### 安全门禁

- 所有 API 和 WebSocket 完成认证与精确权限校验。
- 不存在仓库内固定生产密钥和默认密码。
- 所有秘密字段完成脱敏和加密。
- SSH/SFTP/批量执行具备用户和资产范围审计。
- Docker Agent 只能被后端通过受信通道访问。
- Webhook 完成强制签名、重放防护、路径和 SSRF 防护。
- 完成至少一次 IDOR、SSRF、路径穿越和权限绕过专项测试。

### 工程门禁

- `npm run build` 成功。
- 后端标准测试命令开箱即用。
- CI 中前后端测试、类型检查、Lint 和生产构建全部成功。
- 数据库变更全部通过 Alembic 管理。
- 后台任务支持重试、幂等和重启恢复。

### 运行门禁

- Readiness/Liveness 正常。
- 容器非 root 运行。
- 完成数据库备份恢复演练。
- 日志、指标、告警和审计可关联。
- 完成至少一次部署失败恢复和回滚演练。

### UI 门禁

- 核心业务页面完成桌面与移动端浏览器验收。
- 菜单、路由、按钮和后端权限保持一致。
- 键盘可操作，关键控件具有正确 ARIA。
- 空状态、加载状态、错误状态和权限不足状态统一。
- 全局设计 Token 和视觉语言统一。

---

## 13. 最终评价

这个项目的主要问题不是“功能太少”，而是：

> 功能建设速度已经明显超过安全治理、测试体系和生产可靠性建设速度。

正面来看，它已经具备：

- 比较完整的运维产品范围。
- 清晰的前后端结构。
- 可继续演进的业务模型。
- 真实可用的监控、巡检、工单、AI 和发布骨架。
- 一定的 UI 完成度。

但当前最大的上线阻断项非常明确：

1. 身份令牌可以被伪造。
2. SSH/SFTP/批量执行等远程控制入口没有完整认证。
3. Docker Agent 接近裸露的主机 Root 控制接口。
4. 凭据和系统 Secret 保护不足。
5. 部署 Webhook 存在路径穿越和 SSRF 风险。
6. 正式前端类型构建尚未通过。
7. 后台任务、迁移和调度机制不具备多实例生产可靠性。

因此，当前版本的定位是：

> **产品功能完成度中上；工程质量中等；生产可靠性偏低；安全性严重不达标。**

建议不要推倒重写。优先完成 P0 安全止血，再补权限闭环、类型构建、可靠任务队列和数据库迁移。完成这些后，整体成熟度有机会从当前约 48 分提升到 70～75 分；随后再通过测试体系、密钥治理、UI 统一和多实例可靠性建设，逐步达到正式生产标准。
