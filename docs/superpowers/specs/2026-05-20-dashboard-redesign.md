# 仪表盘重设计方案

## 概述

将运维平台仪表盘从标准管理后台模板风格升级为数据驱动风格（类 Vercel/Linear），提升信息密度和视觉品质。

## 设计方向

- 浅色背景 + 白色卡片 + 圆角 + 轻阴影
- 统计卡片增加 Sparkline 趋势图和变化百分比
- 下方主内容区改为活动时间线 + 图表混排
- 所有数据来自真实后端 API

## 页面结构

### 1. 顶部栏

- 左侧：问候语（早上好/下午好/晚上好）+ 当前日期
- 右侧：时间筛选 tabs（今天 / 本周 / 本月），默认"今天"

### 2. 统计卡片（4 列 grid）

| 卡片 | 指标 | Sparkline 数据 |
|------|------|----------------|
| 资产总数 | asset_total | 近 7 天每日资产数 |
| 在线主机 | online_hosts | 近 7 天每日在线数 |
| 待处理告警 | open_alerts | 近 7 天每日告警数 |
| 待处理工单 | pending_tickets | 近 7 天每日工单数 |

每张卡片包含：
- 图标 + 标签
- 大号数值
- Sparkline 迷你趋势图（SVG polyline，30-40px 高）
- 变化百分比（如 `+12%`，绿色/红色）

### 3. 主内容区（grid: 2fr 1fr）

#### 左侧：活动时间线

- 标题"最近活动"+ 分类筛选 tabs（全部 / 告警 / 工单 / 资产 / 巡检 / 用户）
- 每条事件：彩色圆点 + 事件描述 + 时间 + 类型标签
- 支持加载更多（分页）
- 数据来源：审计日志 API

#### 右侧：图表区

**告警趋势图**
- 近 7 天每日告警数量的 SVG 面积图
- X 轴：日期，Y 轴：数量

**资产类型分布**
- 横向条形图（Linux / K8s / Docker 等）
- 百分比 + 数量

## 后端 API 设计

### GET /api/v1/dashboard/sparkline

返回近 7 天每日统计。

```json
{
  "code": 0,
  "data": {
    "dates": ["05-14", "05-15", "05-16", "05-17", "05-18", "05-19", "05-20"],
    "series": {
      "assets": [120, 122, 123, 125, 126, 127, 128],
      "online": [90, 91, 93, 94, 95, 95, 96],
      "alerts": [2, 3, 1, 4, 3, 5, 5],
      "tickets": [8, 10, 9, 11, 10, 12, 12]
    }
  }
}
```

实现方式：查询各表的 `created_at` 按天分组计数。对于资产和在线数，用当天最新快照值。

### GET /api/v1/dashboard/activities

返回最近的审计日志条目。

参数：
- `limit`：条数，默认 20
- `type`：筛选类型（alert/ticket/asset/patrol/user），可选

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "time": "2026-05-20T10:20:00",
        "description": "CPU 使用率告警 — web-01",
        "detail": "CPU 使用率超过 90%",
        "type": "alert",
        "type_label": "告警"
      }
    ]
  }
}
```

实现方式：查询 `audit_logs` 表，按 `created_at` 倒序，根据 `target_type` 映射分类。

### GET /api/v1/dashboard/alert-trend

返回近 7 天每日告警数量。

```json
{
  "code": 0,
  "data": {
    "dates": ["05-14", "05-15", "05-16", "05-17", "05-18", "05-19", "05-20"],
    "counts": [2, 3, 1, 4, 3, 5, 5]
  }
}
```

实现方式：查询 `alert_events` 表的 `created_at` 按天分组计数。

## 前端改动

### DashboardView.vue（重写）

- 移除现有的 5 个面板（资产变更、工单、告警、角色分布、资产类型）
- 移除快捷统计条
- 新布局：顶部栏 → 统计卡片 grid → 主内容区（时间线 + 图表）
- 所有图表用纯 SVG 实现，不引入第三方图表库

### 新增组件

- `Sparkline.vue`：接受 `data: number[]` 和 `color: string`，渲染 SVG polyline
- `AlertTrendChart.vue`：接受 `dates: string[]` 和 `counts: number[]`，渲染 SVG 面积图

### API 调用

- `src/api/dashboard.ts`：新增 `getSparkline()`、`getActivities()`、`getAlertTrend()` 三个函数
- `onMounted` 中并行请求所有 4 个 API

## 不在范围内

- 不引入 ECharts / Chart.js 等图表库
- 不实现实时 WebSocket 推送
- 不改动其他页面
- 时间筛选 tabs 暂不实现时间范围切换（默认展示近 7 天数据，tabs 仅做 UI 展示）
