# Emergency Entry Shutdown and Docker Agent Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Default-close unauthenticated high-risk entry points and clarify the complete Docker Agent build, publish, deploy, and registration workflow.

**Architecture:** A pure environment-backed security-control module drives a testable API-router factory and a deploy Webhook guard. A small frontend utility generates deterministic Agent commands for a three-step registration wizard.

**Tech Stack:** FastAPI, Python, pytest, Vue 3, TypeScript, Element Plus, Node test runner.

---

### Task 1: Add failing backend security-control tests

**Files:**
- Create: `backend/tests/test_security_controls.py`

- [ ] Test boolean parsing and default-disabled controls.
- [ ] Test that the API router omits high-risk paths by default.
- [ ] Test that explicitly enabled controls restore only the selected routes.
- [ ] Test the disabled-feature HTTP 503 guard.
- [ ] Run the targeted test and confirm it fails before implementation.

### Task 2: Implement backend emergency controls

**Files:**
- Create: `backend/app/core/security_controls.py`
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/api/deploy.py`
- Modify: `docker/docker-compose.yml`
- Modify: `docker/.env.example`
- Modify: `.env.example`

- [ ] Implement immutable environment controls with safe false defaults.
- [ ] Refactor API router construction into a factory.
- [ ] Conditionally register SSH Terminal, SFTP, Batch Exec, and SSH Key routers.
- [ ] Add the deploy artifact Webhook feature guard.
- [ ] Expose explicit Compose environment mappings and examples.
- [ ] Run targeted backend tests and confirm they pass.

### Task 3: Add failing Docker Agent command tests

**Files:**
- Create: `frontend/tests/dockerAgentSetup.test.mjs`

- [ ] Test build, login, push, pull, and run command generation.
- [ ] Test management-IP port binding and endpoint generation.
- [ ] Assert the Docker registration dialog contains three operational steps.
- [ ] Run the targeted test and confirm it fails before implementation.

### Task 4: Implement the three-step registration wizard

**Files:**
- Create: `frontend/src/utils/dockerAgentSetup.ts`
- Modify: `frontend/src/views/containers/DockerView.vue`
- Modify: `agent/README.md`
- Modify: `agent/Dockerfile`

- [ ] Implement command-generation helpers.
- [ ] Add image-reference and management-IP inputs.
- [ ] Add separate publish and deployment command blocks with copy actions.
- [ ] Add previous/next validation and endpoint suggestion.
- [ ] Update Agent documentation to use user-owned registry examples.
- [ ] Run targeted frontend tests and confirm they pass.

### Task 5: Verify and commit

- [ ] Run all backend tests with the required Python path.
- [ ] Run all frontend Node tests.
- [ ] Run `npm run build` and report any pre-existing failures separately.
- [ ] Run `npx vite build` to verify production bundling.
- [ ] Run `git diff --check` and inspect the scoped diff.
- [ ] Commit only files created or modified by this task.