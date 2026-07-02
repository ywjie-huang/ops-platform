# Dashboard Duty Homepage Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone localhost preview that demonstrates the proposed duty-focused dashboard direction without touching existing production dashboard code.

**Architecture:** Add a self-contained HTML prototype under `frontend/preview/` and serve that directory locally with a lightweight static server. Keep the preview visually aligned with the repo's existing product tokens and shell patterns.

**Tech Stack:** Static HTML, CSS, small inline JavaScript, local Python HTTP server

---

### Task 1: Create the preview artifact

**Files:**
- Create: `frontend/preview/dashboard-duty-preview.html`

- [ ] Draft a standalone page with a simulated app shell
- [ ] Build a top risk strip with action-oriented metrics
- [ ] Build a dominant “today focus” section with clear severity states
- [ ] Add secondary sections for shortcuts, alert trend, asset mix, and recent activity
- [ ] Add responsive behavior for tablet and mobile widths

### Task 2: Verify and serve locally

**Files:**
- Reuse: `frontend/preview/dashboard-duty-preview.html`

- [ ] Open the preview in a local browser via HTTP
- [ ] Check desktop and mobile layouts
- [ ] Confirm the page is readable without broken assets or script errors
- [ ] Share the localhost URL with the user
