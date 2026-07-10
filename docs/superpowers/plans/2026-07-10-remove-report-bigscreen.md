# Remove Report Bigscreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `/bigscreen` child page and its page-private components while preserving the dashboard, report center, and unrelated working-tree edits.

**Architecture:** Make a surgical router edit, delete only components proven to be exclusively referenced by `BigScreenView.vue`, and add a route-level regression test. Existing dashboard APIs and permissions remain unchanged because they are used by `DashboardView.vue`.

**Tech Stack:** Vue 3, Vue Router, TypeScript, Node test runner, Vite

---

### Task 1: Add route regression coverage

**Files:**
- Create: `frontend/src/router/modules/reportBigscreenRemoval.test.mjs`

- [ ] Write a Node test that locates the root route group and asserts no child route has path `bigscreen`, name `BigScreen`, or a component loader referencing `BigScreenView.vue`.
- [ ] Run the test and confirm it fails against the current route table.

### Task 2: Remove the page and private components

**Files:**
- Modify: `frontend/src/router/modules/routes.ts`
- Delete: `frontend/src/views/dashboard/BigScreenView.vue`
- Delete: `frontend/src/views/dashboard/components/KpiCard.vue`
- Delete: `frontend/src/views/dashboard/components/MiniLineChart.vue`
- Delete: `frontend/src/views/dashboard/components/RingChart.vue`
- Delete: `frontend/src/views/dashboard/components/BarChart.vue`

- [ ] Remove only the `BigScreen` route block, preserving all unrelated route changes.
- [ ] Verify each delete target resolves inside `D:\my-project\frontend\src\views\dashboard` and delete the five files.
- [ ] Remove the empty `components` directory if no files remain.

### Task 3: Verify and commit

**Files:**
- Test: `frontend/src/router/modules/reportBigscreenRemoval.test.mjs`

- [ ] Run the new route regression test and existing router test.
- [ ] Search source code for stale `BigScreenView`, `BigScreen`, `/bigscreen`, and page-private component references.
- [ ] Run `npm run build` in `frontend`.
- [ ] Review `git diff` and confirm unrelated working-tree changes remain intact.
- [ ] Commit only files belonging to this removal with `refactor(dashboard): remove report bigscreen page`.
