# 主机管理页面重设计

## 目标

改善主机管理页面（AssetListView）的视觉体验和新增资产表单的交互体验。

## 设计方案

### 1. 顶部统计卡片

在页面顶部新增一行 4 个统计卡片，展示资产状态概览：

| 卡片 | 图标背景色 | 数据来源 |
|------|-----------|---------|
| 主机总数 | 蓝色 `#eff6ff` | 所有状态计数之和 |
| 使用中 | 绿色 `#f0fdf4` | `count_assets_by_status["使用中"]` |
| 已关机 | 黄色 `#fffbeb` | `count_assets_by_status["已关机"]` |
| 已删除 | 红色 `#fef2f2` | `count_assets_by_status["已删除"]` |

卡片样式：圆角 10px，内含 40x40 带色圆形图标 + 标签文字（12px, muted）+ 大数字（24px, 800 weight）。

### 2. 表格区域优化

- 移除页面顶部的标题行（"主机管理" + 新增按钮），将"新增资产"按钮移到筛选栏右侧
- 筛选栏左侧放标题"资产列表"，右侧放搜索框 + 类型筛选 + 状态筛选 + 新增按钮
- 表头背景改为 `#f8fafc`，底部 2px 分割线
- 行高增加到 padding 12px，斑马纹背景 `#fafbfc`
- 分页栏改为左右分布：左侧"共 X 条"，右侧页码

### 3. 新增资产表单重构

弹窗宽度保持 580px，表单按逻辑分为 3 组，每组有编号圆形标记 + 蓝色标题：

**第一组：基础信息**
- 名称（必填）、类型（必填，下拉）、IP 地址（必填）、状态（必填，下拉）
- 两列布局

**第二组：规格与系统**
- 规格、操作系统（两列）
- 负责人（单列占满）
- 描述（textarea，单列占满）

**第三组：SSH 连接配置**
- 端口、用户名、密码（三列布局）

## 技术方案

### 后端

新增 API 端点 `GET /api/v1/assets/stats`，返回各状态的资产计数。

已有服务层函数 `count_assets_by_status(db)` 可直接使用。

```python
@router.get("/stats")
def api_asset_stats(db: Session = Depends(get_db), ...):
    counts = count_assets_by_status(db)
    total = sum(counts.values())
    return {"code": 0, "data": {
        "total": total,
        "active": counts.get("使用中", 0),
        "shutdown": counts.get("已关机", 0),
        "deleted": counts.get("已删除", 0),
    }}
```

权限：复用 `assets.view`。

注意：`/stats` 路由必须在 `/{asset_id}` 之前定义，否则 FastAPI 会把 "stats" 当作 asset_id 解析。

### 前端

1. `api/assets.ts` — 新增 `getAssetStats()` 函数
2. `AssetListView.vue` — 重写模板和样式：
   - 新增 stats 相关 ref 和 onMounted 获取
   - 用 CSS grid 实现统计卡片
   - 调整筛选栏布局
   - 表单改为分组布局

### 不涉及的文件

- AssetDetailView — 不改动
- 路由配置 — 不改动
- 其他页面 — 不改动
