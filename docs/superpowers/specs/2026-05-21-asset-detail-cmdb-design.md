# CMDB 资产详情页重设计

## 目标

将资产详情页从简单的 `el-descriptions` 表格改为正规 CMDB 风格的 Tab 页签布局。

## 设计方案

### 页面结构

#### 1. 顶部 Header

白色背景单行布局，从左到右：
- 返回按钮（`← 返回`，`$router.back()`）
- 资产名称（18px, 700 weight）
- IP 地址（13px, monospace, muted）
- 状态标签（`el-tag`，复用现有颜色映射）
- 类型标签（灰色背景小标签）
- 操作按钮靠右：SSH 连接（primary）、编辑（default）

#### 2. Tab 区域

4 个 Tab，使用 `el-tabs` 组件：

**Tab 1：基础信息**（默认选中）
- 2 列网格布局
- 字段：资产名称、资产类型、IP 地址、状态、负责人、创建时间、规格、操作系统
- 底部单列：说明（description）

**Tab 2：连接配置**
- 3 列网格布局
- 字段：SSH 端口、用户名、认证方式（密码）

**Tab 3：关联工单**（预留）
- 空状态组件 `el-empty`，提示"暂无关联工单"

**Tab 4：变更记录**（预留）
- 空状态组件 `el-empty`，提示"暂无变更记录"

#### 3. 编辑弹窗

保持现有编辑逻辑和表单字段不变，弹窗宽度 580px。

### 样式规范

- Header 背景：`#fff`，底部 1px 边框 `var(--border-color)`
- Tab 内容区背景：`var(--bg-color)`（`#f4f6fa`）
- 信息卡片：白底圆角 10px，内含字段标题（12px, muted）+ 字段值（14px）
- 使用 CSS 变量：`var(--surface-color)`, `var(--border-color)`, `var(--text-primary)`, `var(--text-muted)`

### 不涉及的文件

- 后端 API — 不改动
- 路由配置 — 不改动
- 资产列表页 — 不改动
