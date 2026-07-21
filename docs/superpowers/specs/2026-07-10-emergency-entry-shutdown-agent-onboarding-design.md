# Emergency Entry Shutdown and Docker Agent Onboarding Design

**Date:** 2026-07-10

## Goal

Complete phase-one item one from the system assessment: default-close the unauthenticated high-risk backend entry points, keep Docker Agent network isolation as a deployment responsibility, and make the Docker host registration wizard explain the complete source-to-image-to-host workflow.

## Approved Scope

- Default-disable SSH Terminal WebSocket, SFTP, and Batch Exec WebSocket route registration.
- SSH Key CRUD is always registered, but requires JWT authentication and `ssh_keys.*` RBAC permissions; responses never return secret plaintext.
- Default-disable the deployment artifact Webhook through an explicit environment feature switch.
- Do not change Docker Agent network behavior in application code in this task.
- Replace the two-step Docker host registration wizard with three steps:
  1. Build and push the Agent image from the repository `agent` directory.
  2. Pull and run the image on the target Docker host.
  3. Register the reachable management-network Agent endpoint in the platform.
- Remove hard-coded private registry assumptions from onboarding documentation and generated commands.

## Backend Design

Introduce immutable emergency-access controls loaded from environment variables. All controls default to `false`. The API router is built through a testable factory, and high-risk routers are included only when their corresponding control is enabled. The deploy router remains available, but the artifact Webhook has an early dependency guard returning HTTP 503 while disabled.

Environment variables:

- `ENABLE_SSH_TERMINAL`
- `ENABLE_SFTP`
- `ENABLE_BATCH_EXEC`
- `ENABLE_DEPLOY_WEBHOOK`

## Frontend Design

The registration dialog becomes a compact three-step operational flow. The user enters an image reference and a Docker management IP. Commands are generated from those inputs and each command block has a copy action. Registration automatically proposes `<management-ip>:9001` as the endpoint without overwriting a manually entered value.

The interface uses existing Element Plus controls and project design tokens. Command blocks remain monospace, responsive, keyboard accessible, and avoid inline styles.

## Validation

- Unit tests for environment boolean parsing and default-closed controls.
- Router-factory tests proving high-risk routes are absent by default and present only when enabled.
- Unit tests for Agent build/publish/run command generation.
- Source integration assertions for the three-step wizard.
- Backend targeted/full tests, frontend Node tests, TypeScript build and Vite build verification.