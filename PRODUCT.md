# Product

## Register

product

## Users

运维工程师和 SRE，日常使用场景是监控大屏前或笔记本上快速排查问题。需要一眼看到异常、快速定位、立即操作。状态通常是专注或紧急（告警触发时焦虑），不是悠闲浏览。

## Product Purpose

统一运维管理平台，将主机监控、告警管理、容器发现、SSH 终端、批量执行、巡检任务、工单协作整合到一个界面。成功标准：运维人员能在 10 秒内发现异常，30 秒内定位问题主机，1 分钟内开始处理。

## Brand Personality

高效、克制、可靠。三个关键词：**precise, calm, trustworthy**。

工具应该消失在任务中。不追求视觉惊艳，追求操作流畅。每个界面元素都为"更快发现问题、更快解决问题"服务。

## Anti-references

- **Datadog 的信息过载**：数据多到需要培训才能看懂。信息密度要高，但不能让人迷失。
- **Grafana 的粗糙感**：功能强大但视觉缺乏打磨，组件样式不统一。
- **传统企业后台的沉闷**：Element Plus 默认主题那种"能用但不好用"的感觉。
- **SaaS landing page 套路**：渐变 hero、统计数据大卡片、marketing 文案。这是工具，不是营销页。

## Design Principles

1. **Earned familiarity.** 用 Linear/Raycast 用户觉得理所当然的标准来要求自己。相同的交互模式，一致的组件词汇。
2. **Density without overwhelm.** 信息密度要高，但层级要清晰。用间距和字重区分层级，不是用更多颜色和装饰。
3. **Tool disappears into task.** 运维人员不应该"欣赏界面"，他们应该直接看到数据、做出判断、执行操作。
4. **Consistency is a feature.** 同样的按钮在两个地方看起来不同，其中一个是错的。同一个视觉词汇贯穿所有页面。
5. **State over decoration.** 每个视觉变化都传达状态（hover、active、loading、error），不是装饰。

## Accessibility & Inclusion

- WCAG 2.1 AA 作为基线
- 色盲友好：不只靠颜色区分状态，配合图标和文字
- 支持 prefers-reduced-motion
- 键盘可导航：所有交互元素需要 tabindex + 键盘事件
- 中文为主，英文术语保持原样（不翻译 SSH、API、CPU 等）

## Design Tokens

```css
--primary-color: #5e6ad2
--primary-hover: #4f5bc4
--primary-bg: rgba(94, 106, 210, 0.08)
--success-color: #22c55e
--warning-color: #f5a623
--danger-color: #e5484d
--bg-color: #fafafa
--surface-color: #ffffff
--border-color: #e8e8e8
--text-primary: #111111
--text-secondary: #666666
--text-muted: #999999
--border-radius: 8px
```

## UI Patterns

- 统计卡片：CSS Grid 4 列，移动端 2x2
- 表格：`.table-wrapper` 包裹支持横向滚动
- 折叠面板：`grid-template-rows` 动画，`aria-expanded` + `role="button"`
- 弹窗：`width="min(Npx, 90vw)"` 响应式宽度
- 空状态：自定义 `#empty` 插槽，引导用户操作
- 相对时间：7 天内显示「x 分钟前」，hover 显示完整时间
