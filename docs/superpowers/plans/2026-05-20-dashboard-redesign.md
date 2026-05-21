# 仪表盘重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将仪表盘从标准管理模板风格升级为数据驱动风格，增加真实数据的 Sparkline 趋势图、活动时间线和告警趋势图。

**Architecture:** 后端新增 3 个 API 端点（sparkline、activities、alert-trend），前端重写 DashboardView.vue 布局，新增 Sparkline 和 AlertTrendChart 两个 SVG 组件。所有图表用纯 SVG 实现，不引入第三方图表库。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (backend), Vue 3 + TypeScript + Element Plus (frontend), 纯 SVG 图表

---

## File Structure

### Backend (new/modified)

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/api/dashboard.py` | Modify | 新增 3 个路由端点 |
| `backend/app/services/dashboard.py` | Modify | 新增 3 个数据构建函数 |

### Frontend (new/modified)

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/api/dashboard.ts` | Modify | 新增 3 个 API 函数 |
| `frontend/src/components/Sparkline.vue` | Create | 迷你趋势图 SVG 组件 |
| `frontend/src/components/AlertTrendChart.vue` | Create | 告警趋势面积图 SVG 组件 |
| `frontend/src/views/dashboard/DashboardView.vue` | Modify | 重写整个仪表盘页面 |

---

## Task 1: Backend — Sparkline API

**Files:**
- Modify: `backend/app/services/dashboard.py`
- Modify: `backend/app/api/dashboard.py`

- [x] **Step 1: 在 `dashboard.py` service 中新增 `build_sparkline_data` 函数**

在 `backend/app/services/dashboard.py` 文件末尾添加：

```python
from datetime import datetime, timedelta
from sqlalchemy import func, select, cast, Date
from app.models.asset import Asset
from app.models.alert import Alert
from app.models.ticket import Ticket
from app.models.alert_event import AlertEvent


def build_sparkline_data(db: Session) -> dict:
    """返回近 7 天每日统计，用于 Sparkline 趋势图。"""
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    date_strs = [d.strftime("%m-%d") for d in dates]

    # 资产总数（取每天的总量，无 created_at 按天分组则用当前总量）
    asset_total = db.scalar(select(func.count(Asset.id))) or 0

    # 在线主机数（状态为"使用中"）
    online_total = db.scalar(
        select(func.count(Asset.id)).where(Asset.status == "使用中")
    ) or 0

    # 告警：近 7 天每日新增告警数（alert_events 表）
    alert_rows = db.scalars(
        select(
            cast(AlertEvent.received_at, Date).label("day"),
            func.count(AlertEvent.id),
        )
        .where(AlertEvent.received_at >= datetime.combine(dates[0], datetime.min.time()))
        .group_by(cast(AlertEvent.received_at, Date))
        .order_by(cast(AlertEvent.received_at, Date))
    ).all()
    alert_map = {str(row[0]): row[1] for row in alert_rows}

    # 工单：近 7 天每日新增工单数
    ticket_rows = db.scalars(
        select(
            cast(Ticket.created_at, Date).label("day"),
            func.count(Ticket.id),
        )
        .where(Ticket.created_at >= datetime.combine(dates[0], datetime.min.time()))
        .group_by(cast(Ticket.created_at, Date))
        .order_by(cast(Ticket.created_at, Date))
    ).all()
    ticket_map = {str(row[0]): row[1] for row in ticket_rows}

    # 对于资产和在线数，无历史快照，用常量填充（后续可接入时序数据库）
    assets_series = [asset_total] * 7
    online_series = [online_total] * 7
    alerts_series = [alert_map.get(str(d), 0) for d in dates]
    tickets_series = [ticket_map.get(str(d), 0) for d in dates]

    return {
        "dates": date_strs,
        "series": {
            "assets": assets_series,
            "online": online_series,
            "alerts": alerts_series,
            "tickets": tickets_series,
        },
    }
```

- [x] **Step 2: 在 `dashboard.py` API 中新增路由**

在 `backend/app/api/dashboard.py` 文件末尾添加：

```python
from app.services.dashboard import build_sparkline_data


@router.get("/sparkline")
def api_dashboard_sparkline(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    data = build_sparkline_data(db)
    return {"code": 0, "data": data}
```

- [x] **Step 3: 验证 API 可用**

重启后端服务后访问 `GET /api/v1/dashboard/sparkline`，确认返回格式正确。

- [x] **Step 4: Commit**

```bash
git add backend/app/services/dashboard.py backend/app/api/dashboard.py
git commit -m "feat(dashboard): add sparkline API for 7-day trend data"
```

---

## Task 2: Backend — Activities API

**Files:**
- Modify: `backend/app/services/dashboard.py`
- Modify: `backend/app/api/dashboard.py`

- [x] **Step 1: 在 `dashboard.py` service 中新增 `build_activities` 函数**

在 `backend/app/services/dashboard.py` 文件末尾添加：

```python
from app.models.audit import AuditLog


# target_type 到前端分类的映射
_ACTIVITY_TYPE_MAP = {
    "asset": "asset",
    "ssh_key": "asset",
    "container": "asset",
    "ticket": "ticket",
    "alert": "alert",
    "alert_event": "alert",
    "patrol": "patrol",
    "user": "user",
    "role": "user",
    "auth": "user",
    "settings": "system",
    "batch_exec": "system",
}

_ACTIVITY_LABEL_MAP = {
    "asset": "资产",
    "ticket": "工单",
    "alert": "告警",
    "patrol": "巡检",
    "user": "用户",
    "system": "系统",
}

_ACTION_MAP = {
    "create": "新增",
    "update": "更新",
    "delete": "删除",
    "login": "登录",
    "logout": "登出",
}

_TONE_MAP = {
    "asset": "blue",
    "ticket": "orange",
    "alert": "red",
    "patrol": "green",
    "user": "purple",
    "system": "default",
}


def build_activities(db: Session, limit: int = 20, activity_type: str | None = None) -> list[dict]:
    """从审计日志构建活动时间线数据。"""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

    if activity_type and activity_type != "all":
        # 反查 target_type
        target_types = [k for k, v in _ACTIVITY_TYPE_MAP.items() if v == activity_type]
        if target_types:
            stmt = stmt.where(AuditLog.target_type.in_(target_types))

    stmt = stmt.limit(limit)
    rows = db.scalars(stmt).all()

    items = []
    for row in rows:
        act_type = _ACTIVITY_TYPE_MAP.get(row.target_type, "system")
        action_label = _ACTION_MAP.get(row.action, row.action)
        items.append({
            "time": row.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": f"{action_label} — {row.target_name}" if row.target_name else action_label,
            "detail": row.detail or "",
            "type": act_type,
            "type_label": _ACTIVITY_LABEL_MAP.get(act_type, "其他"),
            "username": row.username or "",
        })

    return items
```

- [x] **Step 2: 在 `dashboard.py` API 中新增路由**

在 `backend/app/api/dashboard.py` 文件末尾添加：

```python
from app.services.dashboard import build_activities


@router.get("/activities")
def api_dashboard_activities(
    limit: int = 20,
    type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    items = build_activities(db, limit=limit, activity_type=type)
    return {"code": 0, "data": {"items": items}}
```

- [x] **Step 3: 验证 API 可用**

重启后端，访问 `GET /api/v1/dashboard/activities?limit=5` 和 `GET /api/v1/dashboard/activities?type=alert`，确认返回格式正确。

- [x] **Step 4: Commit**

```bash
git add backend/app/services/dashboard.py backend/app/api/dashboard.py
git commit -m "feat(dashboard): add activities timeline API from audit logs"
```

---

## Task 3: Backend — Alert Trend API

**Files:**
- Modify: `backend/app/services/dashboard.py`
- Modify: `backend/app/api/dashboard.py`

- [x] **Step 1: 在 `dashboard.py` service 中新增 `build_alert_trend` 函数**

在 `backend/app/services/dashboard.py` 文件末尾添加：

```python
def build_alert_trend(db: Session) -> dict:
    """返回近 7 天每日告警数量。"""
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    date_strs = [d.strftime("%m-%d") for d in dates]

    rows = db.scalars(
        select(
            cast(AlertEvent.received_at, Date).label("day"),
            func.count(AlertEvent.id),
        )
        .where(AlertEvent.received_at >= datetime.combine(dates[0], datetime.min.time()))
        .group_by(cast(AlertEvent.received_at, Date))
        .order_by(cast(AlertEvent.received_at, Date))
    ).all()
    count_map = {str(row[0]): row[1] for row in rows}

    return {
        "dates": date_strs,
        "counts": [count_map.get(str(d), 0) for d in dates],
    }
```

- [x] **Step 2: 在 `dashboard.py` API 中新增路由**

在 `backend/app/api/dashboard.py` 文件末尾添加：

```python
from app.services.dashboard import build_alert_trend


@router.get("/alert-trend")
def api_dashboard_alert_trend(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    data = build_alert_trend(db)
    return {"code": 0, "data": data}
```

- [x] **Step 3: 验证 API 可用**

重启后端，访问 `GET /api/v1/dashboard/alert-trend`，确认返回格式正确。

- [x] **Step 4: Commit**

```bash
git add backend/app/services/dashboard.py backend/app/api/dashboard.py
git commit -m "feat(dashboard): add alert trend API for 7-day chart"
```

---

## Task 4: Frontend — API 函数

**Files:**
- Modify: `frontend/src/api/dashboard.ts`

- [x] **Step 1: 新增 3 个 API 函数**

将 `frontend/src/api/dashboard.ts` 替换为：

```typescript
import request from './request'

export function getDashboardStats() {
  return request.get('/dashboard/stats')
}

export function getDashboardSummary() {
  return request.get('/dashboard/summary')
}

export function getSparkline() {
  return request.get('/dashboard/sparkline')
}

export function getActivities(limit = 20, type?: string) {
  const params: any = { limit }
  if (type && type !== 'all') params.type = type
  return request.get('/dashboard/activities', { params })
}

export function getAlertTrend() {
  return request.get('/dashboard/alert-trend')
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/api/dashboard.ts
git commit -m "feat(dashboard): add frontend API functions for new endpoints"
```

---

## Task 5: Frontend — Sparkline 组件

**Files:**
- Create: `frontend/src/components/Sparkline.vue`

- [x] **Step 1: 创建 Sparkline 组件**

```vue
<template>
  <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`">
    <polyline
      :points="points"
      fill="none"
      :stroke="color"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <polygon
      :points="areaPoints"
      :fill="color"
      fill-opacity="0.1"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  data: number[]
  color?: string
  width?: number
  height?: number
}>(), {
  color: '#3b82f6',
  width: 80,
  height: 32,
})

const points = computed(() => {
  const { data, width, height } = props
  if (!data.length) return ''
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const step = width / (data.length - 1 || 1)
  return data.map((v, i) => {
    const x = i * step
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')
})

const areaPoints = computed(() => {
  const { data, width, height } = props
  if (!data.length) return ''
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const step = width / (data.length - 1 || 1)
  const linePoints = data.map((v, i) => {
    const x = i * step
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')
  return `${linePoints} ${width},${height} 0,${height}`
})
</script>
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/components/Sparkline.vue
git commit -m "feat(dashboard): add Sparkline SVG component"
```

---

## Task 6: Frontend — AlertTrendChart 组件

**Files:**
- Create: `frontend/src/components/AlertTrendChart.vue`

- [x] **Step 1: 创建 AlertTrendChart 组件**

```vue
<template>
  <div class="alert-trend">
    <div class="chart-header">
      <span class="chart-title">告警趋势</span>
      <span class="chart-subtitle">近 7 天</span>
    </div>
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" class="chart-svg">
      <!-- 面积 -->
      <polygon :points="areaPoints" fill="#ef4444" fill-opacity="0.08" />
      <!-- 线条 -->
      <polyline :points="linePoints" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <!-- 数据点 -->
      <circle
        v-for="(p, i) in dotPositions"
        :key="i"
        :cx="p.x"
        :cy="p.y"
        r="3"
        fill="#fff"
        stroke="#ef4444"
        stroke-width="1.5"
      />
    </svg>
    <div class="chart-labels">
      <span v-for="d in dates" :key="d">{{ d }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  dates: string[]
  counts: number[]
  width?: number
  height?: number
}>(), {
  width: 280,
  height: 100,
})

const padding = { top: 10, right: 10, bottom: 0, left: 10 }

const chartWidth = computed(() => props.width - padding.left - padding.right)
const chartHeight = computed(() => props.height - padding.top - padding.bottom)

const maxVal = computed(() => Math.max(...props.counts, 1))

const points = computed(() => {
  const { counts } = props
  if (!counts.length) return []
  const step = chartWidth.value / (counts.length - 1 || 1)
  return counts.map((v, i) => ({
    x: padding.left + i * step,
    y: padding.top + chartHeight.value - (v / maxVal.value) * chartHeight.value,
  }))
})

const linePoints = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))

const areaPoints = computed(() => {
  const pts = points.value
  if (!pts.length) return ''
  const last = pts[pts.length - 1]
  const first = pts[0]
  return `${linePoints.value} ${last.x},${padding.top + chartHeight.value} ${first.x},${padding.top + chartHeight.value}`
})

const dotPositions = computed(() => points.value)
</script>

<style scoped>
.alert-trend {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid var(--border-color, #e5e7eb);
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.chart-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}
.chart-subtitle {
  font-size: 12px;
  color: #94a3b8;
}
.chart-svg {
  display: block;
}
.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: #94a3b8;
}
</style>
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/components/AlertTrendChart.vue
git commit -m "feat(dashboard): add AlertTrendChart SVG component"
```

---

## Task 7: Frontend — 重写 DashboardView

**Files:**
- Modify: `frontend/src/views/dashboard/DashboardView.vue`

- [x] **Step 1: 替换整个 DashboardView.vue**

将 `frontend/src/views/dashboard/DashboardView.vue` 替换为：

```vue
<template>
  <div class="dashboard">
    <!-- 顶部栏 -->
    <div class="dashboard-header">
      <div>
        <h2 class="greeting">{{ greeting }}，{{ authStore.fullName || '管理员' }}</h2>
        <p class="date-text">{{ currentDate }}</p>
      </div>
      <div class="time-tabs">
        <span
          v-for="tab in timeTabs"
          :key="tab.key"
          class="time-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >{{ tab.label }}</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="stat-card-top">
          <span class="stat-card-label">{{ card.label }}</span>
          <div class="stat-card-icon" :style="{ background: card.iconBg }">
            <el-icon :size="16" :style="{ color: card.iconColor }"><component :is="card.icon" /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ card.value }}</div>
        <div class="stat-card-bottom">
          <Sparkline :data="card.sparkline" :color="card.iconColor" :width="80" :height="28" />
          <span class="stat-change" :class="card.changeType">
            {{ card.change }}
          </span>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-grid">
      <!-- 左侧：活动时间线 -->
      <div class="activity-panel">
        <div class="panel-header">
          <h3>最近活动</h3>
          <div class="filter-tabs">
            <span
              v-for="f in activityFilters"
              :key="f.key"
              class="filter-tab"
              :class="{ active: activeFilter === f.key }"
              @click="handleFilterChange(f.key)"
            >{{ f.label }}</span>
          </div>
        </div>
        <div class="activity-list">
          <div v-for="(item, i) in activities" :key="i" class="activity-item">
            <div class="activity-dot" :class="'dot-' + item.type"></div>
            <div class="activity-body">
              <div class="activity-desc">{{ item.description }}</div>
              <div class="activity-meta">
                <span>{{ item.time }}</span>
                <span v-if="item.username"> · {{ item.username }}</span>
              </div>
            </div>
            <span class="activity-tag" :class="'tag-' + item.type">{{ item.type_label }}</span>
          </div>
          <div v-if="!activities.length" class="empty-hint">暂无活动记录</div>
        </div>
      </div>

      <!-- 右侧：图表 -->
      <div class="side-charts">
        <AlertTrendChart :dates="alertTrend.dates" :counts="alertTrend.counts" />
        <div class="type-panel">
          <div class="panel-header">
            <h3>资产类型</h3>
          </div>
          <div class="bar-list">
            <div v-for="item in typeBreakdown" :key="item.label" class="bar-item">
              <div class="bar-label">{{ item.label }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: typePct(item.value) + '%', background: item.color }"></div>
              </div>
              <div class="bar-value">{{ item.value }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDashboardStats, getSparkline, getActivities, getAlertTrend, getDashboardSummary } from '@/api/dashboard'
import { useAuthStore } from '@/stores/modules/auth'
import { Box, Monitor, Warning, Tickets } from '@element-plus/icons-vue'
import Sparkline from '@/components/Sparkline.vue'
import AlertTrendChart from '@/components/AlertTrendChart.vue'

const authStore = useAuthStore()

const stats = ref<any>({})
const sparkline = ref<any>({ dates: [], series: { assets: [], online: [], alerts: [], tickets: [] } })
const activities = ref<any[]>([])
const alertTrend = ref<any>({ dates: [], counts: [] })
const summary = ref<any>({})

const activeTab = ref('today')
const activeFilter = ref('all')

const timeTabs = [
  { key: 'today', label: '今天' },
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
]

const activityFilters = [
  { key: 'all', label: '全部' },
  { key: 'alert', label: '告警' },
  { key: 'ticket', label: '工单' },
  { key: 'asset', label: '资产' },
  { key: 'patrol', label: '巡检' },
  { key: 'user', label: '用户' },
]

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
})

const statCards = computed(() => {
  const s = sparkline.value.series
  const changePct = (arr: number[]) => {
    if (!arr || arr.length < 2 || arr[arr.length - 2] === 0) return { text: '持平', type: 'neutral' }
    const pct = Math.round(((arr[arr.length - 1] - arr[arr.length - 2]) / arr[arr.length - 2]) * 100)
    if (pct > 0) return { text: `+${pct}%`, type: 'up' }
    if (pct < 0) return { text: `${pct}%`, type: 'down' }
    return { text: '持平', type: 'neutral' }
  }

  const assets = changePct(s.assets)
  const online = changePct(s.online)
  const alertsChange = changePct(s.alerts)
  const tickets = changePct(s.tickets)

  return [
    {
      label: '资产总数', value: stats.value.asset_total ?? '-',
      icon: Box, iconBg: '#eff6ff', iconColor: '#3b82f6',
      sparkline: s.assets || [], change: assets.text, changeType: assets.type,
    },
    {
      label: '在线主机', value: stats.value.online_hosts ?? '-',
      icon: Monitor, iconBg: '#f0fdf4', iconColor: '#22c55e',
      sparkline: s.online || [], change: online.text, changeType: online.type,
    },
    {
      label: '待处理告警', value: stats.value.open_alerts ?? '-',
      icon: Warning, iconBg: '#fef2f2', iconColor: '#ef4444',
      sparkline: s.alerts || [], change: alertsChange.text, changeType: alertsChange.type,
    },
    {
      label: '待处理工单', value: stats.value.pending_tickets ?? '-',
      icon: Tickets, iconBg: '#fffbeb', iconColor: '#f59e0b',
      sparkline: s.tickets || [], change: tickets.text, changeType: tickets.type,
    },
  ]
})

const typeBreakdown = computed(() => summary.value.type_breakdown || [])
const maxTypeValue = computed(() => summary.value.max_type_value || 1)
function typePct(val: number) { return Math.round((val / maxTypeValue.value) * 100) }

async function fetchActivities(type?: string) {
  try {
    const res: any = await getActivities(20, type)
    activities.value = res.data?.items || []
  } catch { activities.value = [] }
}

function handleFilterChange(key: string) {
  activeFilter.value = key
  fetchActivities(key === 'all' ? undefined : key)
}

onMounted(async () => {
  try {
    const [statsRes, sparkRes, actRes, trendRes, sumRes]: any = await Promise.all([
      getDashboardStats(),
      getSparkline(),
      getActivities(20),
      getAlertTrend(),
      getDashboardSummary(),
    ])
    stats.value = statsRes.data
    sparkline.value = sparkRes.data
    activities.value = actRes.data?.items || []
    alertTrend.value = trendRes.data
    summary.value = sumRes.data
  } catch {}
})
</script>

<style lang="scss" scoped>
.dashboard {
  width: 100%;
  padding-right: 16px;
}

// ── 顶部栏 ──
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.greeting {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}
.date-text {
  font-size: 13px;
  color: #94a3b8;
}
.time-tabs {
  display: flex;
  gap: 4px;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 3px;
}
.time-tab {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  &.active {
    background: #fff;
    color: #1e293b;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
}

// ── 统计卡片 ──
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  transition: box-shadow 0.2s;
  &:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
}
.stat-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.stat-card-label {
  font-size: 13px;
  color: #94a3b8;
}
.stat-card-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-card-value {
  font-size: 28px;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 10px;
}
.stat-card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-change {
  font-size: 12px;
  font-weight: 600;
  &.up { color: #22c55e; }
  &.down { color: #ef4444; }
  &.neutral { color: #94a3b8; }
}

// ── 主内容区 ──
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

// ── 活动时间线 ──
.activity-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  h3 {
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
  }
}
.filter-tabs {
  display: flex;
  gap: 4px;
}
.filter-tab {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  &.active {
    background: #e0e7ff;
    color: #4f46e5;
    font-weight: 600;
  }
  &:hover:not(.active) {
    background: #f1f5f9;
  }
}
.activity-list {
  display: flex;
  flex-direction: column;
}
.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
  &:last-child { border-bottom: none; }
}
.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  &.dot-alert { background: #ef4444; }
  &.dot-ticket { background: #f59e0b; }
  &.dot-asset { background: #3b82f6; }
  &.dot-patrol { background: #22c55e; }
  &.dot-user { background: #8b5cf6; }
  &.dot-system { background: #94a3b8; }
}
.activity-body {
  flex: 1;
  min-width: 0;
}
.activity-desc {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.activity-meta {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}
.activity-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
  &.tag-alert { background: #fef2f2; color: #ef4444; }
  &.tag-ticket { background: #fffbeb; color: #f59e0b; }
  &.tag-asset { background: #eff6ff; color: #3b82f6; }
  &.tag-patrol { background: #f0fdf4; color: #22c55e; }
  &.tag-user { background: #f5f3ff; color: #8b5cf6; }
  &.tag-system { background: #f1f5f9; color: #64748b; }
}
.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: #94a3b8;
  font-size: 13px;
}

// ── 右侧图表 ──
.side-charts {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.type-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
}
.bar-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bar-label {
  width: 60px;
  font-size: 12px;
  color: #64748b;
  text-align: right;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}
.bar-value {
  width: 30px;
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
  text-align: right;
}

// ── 响应式 ──
@media (min-width: 1600px) {
  .stat-card-value { font-size: 32px; }
  .dashboard-grid { grid-template-columns: 2fr 420px; }
}
@media (min-width: 1920px) {
  .stat-grid { gap: 20px; }
  .stat-card { padding: 22px; }
  .stat-card-value { font-size: 36px; }
  .dashboard-grid { grid-template-columns: 2fr 480px; gap: 20px; }
}
@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .dashboard-grid { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .stat-grid { grid-template-columns: 1fr; }
}
</style>
```

- [x] **Step 2: 验证页面**

启动前端开发服务器，访问仪表盘页面，确认：
- 4 张统计卡片正常显示，有 Sparkline 趋势图和变化百分比
- 活动时间线正常加载，筛选功能可用
- 告警趋势图和资产类型分布正常显示
- 响应式布局在不同屏幕宽度下正常

- [x] **Step 3: Commit**

```bash
git add frontend/src/views/dashboard/DashboardView.vue
git commit -m "feat(dashboard): redesign dashboard with sparklines, activity timeline, and alert trend chart"
```

---

## Task 8: Final Commit

- [x] **Step 1: 全量验证**

确认所有功能正常：
- 访问仪表盘，所有数据加载正常
- Sparkline 显示近 7 天趋势
- 活动时间线可筛选
- 告警趋势图正确渲染
- 大屏/笔记本/手机宽度下布局正常

- [x] **Step 2: Push**

```bash
git push origin main
```
