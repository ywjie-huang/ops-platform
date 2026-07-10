# 删除报表大屏子页面设计

## 目标

移除顶层“报表大屏”导航分组下名为“报表大屏”的 `/bigscreen` 子页面，不影响同分组内的“仪表盘”和“报表中心”。

## 范围

- 从 `frontend/src/router/modules/routes.ts` 删除 `BigScreen` 子路由。
- 删除 `frontend/src/views/dashboard/BigScreenView.vue`。
- 删除仅由该页面引用的 `KpiCard.vue`、`MiniLineChart.vue`、`RingChart.vue`、`BarChart.vue`。
- 添加路由回归测试，防止 `/bigscreen` 被意外恢复。

## 保留项

- 保留 `/dashboard` 仪表盘及其前后端 API、权限、工具函数和测试。
- 保留 `/reports` 报表中心及详情页。
- 保留顶层“报表大屏”导航分组。
- 不触碰工作区中其他未提交修改，尤其是路由文件里的部署上传路由变更。

## 验收

- 路由表中不存在 `BigScreen`、`bigscreen` 和 `BigScreenView.vue` 引用。
- 专用页面和组件文件不存在。
- 路由回归测试通过。
- 前端生产构建通过。
