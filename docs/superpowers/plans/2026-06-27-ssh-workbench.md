# SSH Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the SSH page into a terminal-heavy workbench with session tabs, on-demand split panes, and a persistent right-side file collaboration area for ops-heavy workflows.

**Architecture:** Keep the existing SSH WebSocket and SFTP APIs, but reorganize the frontend around a workbench state model: tabs organize sessions, panes render layout, and the right panel stays persistent for file collaboration. Implement the first release entirely in the Vue frontend by decomposing the current monolithic SSH view into focused workbench components and pane-scoped connection state.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Element Plus, xterm.js, Vite, existing `@/api/assets`, `@/api/sshKeys`, `@/api/sftp`

---

## File Structure

### Existing files to modify

- `frontend/src/views/monitoring/SSHTerminalView.vue`
  - Replace the current single-terminal page shell with the workbench host view.
- `frontend/src/views/monitoring/ssh/SSHTerminalToolbar.vue`
  - Slim it down into a global control strip for the active pane and workbench toggles.
- `frontend/src/views/monitoring/ssh/SSHLoginForm.vue`
  - Reframe the login overlay around session creation and reconnect flows.
- `frontend/src/views/monitoring/ssh/SFTPFilePanel.vue`
  - Convert from slide-in drawer behavior to a persistent right-side collaboration panel.
- `frontend/src/views/monitoring/ssh/FileEditDialog.vue`
  - Either simplify for fallback editing or turn into a secondary path while the right panel becomes primary.
- `frontend/src/views/monitoring/ssh/sshConnection.ts`
  - Reuse auth payload helpers and extend for pane-level session defaults.

### New files to create

- `frontend/src/views/monitoring/ssh/types.ts`
  - Shared workbench state types.
- `frontend/src/views/monitoring/ssh/useSSHWorkbench.ts`
  - Central workbench state and pane/tab actions.
- `frontend/src/views/monitoring/ssh/SSHTabBar.vue`
  - Session tab strip.
- `frontend/src/views/monitoring/ssh/SSHPaneGrid.vue`
  - Single/split layout host.
- `frontend/src/views/monitoring/ssh/SSHPane.vue`
  - One pane = one xterm instance + one WebSocket connection.
- `frontend/src/views/monitoring/ssh/SSHStatusBar.vue`
  - Bottom workbench status line.
- `frontend/src/views/monitoring/ssh/SSHRightPanel.vue`
  - Tabs for Files / Preview / Actions / Info.
- `frontend/src/views/monitoring/ssh/sshWorkbench.test.mjs`
  - State-model tests for tabs, panes, split behavior.

### Test files

- `frontend/src/views/monitoring/ssh/sshConnection.test.mjs`
  - Extend if helper behavior changes.
- `frontend/src/views/monitoring/ssh/sshWorkbench.test.mjs`
  - New tests for workbench state transitions.

## Task 1: Define the workbench state model

**Files:**
- Create: `frontend/src/views/monitoring/ssh/types.ts`
- Create: `frontend/src/views/monitoring/ssh/useSSHWorkbench.ts`
- Test: `frontend/src/views/monitoring/ssh/sshWorkbench.test.mjs`

- [ ] **Step 1: Write the failing workbench state tests**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  createInitialWorkbenchState,
  createSessionTab,
  splitActiveTab,
  closePane,
  setActivePane,
} from './useSSHWorkbench.ts'

test('creates one default tab with one pane', () => {
  const state = createInitialWorkbenchState()
  assert.equal(state.tabs.length, 1)
  assert.equal(state.tabs[0].panes.length, 1)
  assert.equal(state.activeTabId, state.tabs[0].id)
  assert.equal(state.activePaneId, state.tabs[0].panes[0].id)
})

test('splitActiveTab creates a second pane and keeps layout metadata', () => {
  const state = createInitialWorkbenchState()
  splitActiveTab(state, 'vertical')
  const activeTab = state.tabs[0]
  assert.equal(activeTab.layout, 'vertical')
  assert.equal(activeTab.panes.length, 2)
})

test('closePane collapses split tab back to single pane', () => {
  const state = createInitialWorkbenchState()
  splitActiveTab(state, 'horizontal')
  const [, secondPane] = state.tabs[0].panes
  setActivePane(state, secondPane.id)
  closePane(state, secondPane.id)
  assert.equal(state.tabs[0].layout, 'single')
  assert.equal(state.tabs[0].panes.length, 1)
})

test('createSessionTab appends a disconnected tab and activates it', () => {
  const state = createInitialWorkbenchState()
  const tab = createSessionTab('prod-web-01')
  state.tabs.push(tab)
  state.activeTabId = tab.id
  state.activePaneId = tab.panes[0].id
  assert.equal(state.tabs.at(-1)?.status, 'idle')
  assert.equal(state.activeTabId, tab.id)
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: FAIL with module-not-found or missing export errors for `useSSHWorkbench.ts`.

- [ ] **Step 3: Write the shared workbench types**

```ts
export type SSHConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

export type SSHPaneLayout = 'single' | 'vertical' | 'horizontal'

export interface SSHPaneState {
  id: string
  title: string
  status: SSHConnectionStatus
  hostLabel: string
  currentPath: string
  authMode: string
  fontSize: number
  connectionSeconds: number
  dirtyFilePath: string
  lastError: string
}

export interface SSHTabState {
  id: string
  title: string
  pinned: boolean
  status: SSHConnectionStatus
  layout: SSHPaneLayout
  panes: SSHPaneState[]
}

export interface SSHWorkbenchState {
  activeTabId: string
  activePaneId: string
  rightPanelTab: 'files' | 'preview' | 'actions' | 'info'
  rightPanelOpen: boolean
  tabs: SSHTabState[]
}
```

- [ ] **Step 4: Write the minimal workbench store helpers**

```ts
import type { SSHPaneLayout, SSHPaneState, SSHTabState, SSHWorkbenchState } from './types'

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`
}

function createPane(title = 'Terminal 1'): SSHPaneState {
  return {
    id: uid('pane'),
    title,
    status: 'idle',
    hostLabel: '',
    currentPath: '/',
    authMode: 'asset',
    fontSize: 14,
    connectionSeconds: 0,
    dirtyFilePath: '',
    lastError: '',
  }
}

export function createSessionTab(title = 'New Session'): SSHTabState {
  return {
    id: uid('tab'),
    title,
    pinned: false,
    status: 'idle',
    layout: 'single',
    panes: [createPane()],
  }
}

export function createInitialWorkbenchState(): SSHWorkbenchState {
  const firstTab = createSessionTab()
  return {
    activeTabId: firstTab.id,
    activePaneId: firstTab.panes[0].id,
    rightPanelTab: 'files',
    rightPanelOpen: true,
    tabs: [firstTab],
  }
}

export function setActivePane(state: SSHWorkbenchState, paneId: string) {
  state.activePaneId = paneId
}

export function splitActiveTab(state: SSHWorkbenchState, layout: Exclude<SSHPaneLayout, 'single'>) {
  const tab = state.tabs.find((item) => item.id === state.activeTabId)
  if (!tab || tab.panes.length > 1) return
  tab.layout = layout
  tab.panes.push(createPane('Terminal 2'))
}

export function closePane(state: SSHWorkbenchState, paneId: string) {
  const tab = state.tabs.find((item) => item.id === state.activeTabId)
  if (!tab) return
  tab.panes = tab.panes.filter((pane) => pane.id !== paneId)
  if (tab.panes.length === 0) tab.panes = [createPane()]
  if (tab.panes.length === 1) tab.layout = 'single'
  state.activePaneId = tab.panes[0].id
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: PASS with 4 passing tests.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/monitoring/ssh/types.ts frontend/src/views/monitoring/ssh/useSSHWorkbench.ts frontend/src/views/monitoring/ssh/sshWorkbench.test.mjs
git commit -m "feat(ssh): add workbench session state model"
```

## Task 2: Build the session tab strip and split controls

**Files:**
- Create: `frontend/src/views/monitoring/ssh/SSHTabBar.vue`
- Modify: `frontend/src/views/monitoring/ssh/SSHTerminalToolbar.vue`
- Modify: `frontend/src/views/monitoring/SSHTerminalView.vue`
- Test: `frontend/src/views/monitoring/ssh/sshWorkbench.test.mjs`

- [ ] **Step 1: Extend the state tests for tab actions**

```js
import { addTab, removeTab, renameTab } from './useSSHWorkbench.ts'

test('addTab activates the new tab', () => {
  const state = createInitialWorkbenchState()
  addTab(state, 'db-maint')
  assert.equal(state.tabs.length, 2)
  assert.equal(state.tabs[1].title, 'db-maint')
  assert.equal(state.activeTabId, state.tabs[1].id)
})

test('removeTab falls back to the previous tab', () => {
  const state = createInitialWorkbenchState()
  addTab(state, 'b')
  const second = state.tabs[1]
  removeTab(state, second.id)
  assert.equal(state.tabs.length, 1)
  assert.equal(state.activeTabId, state.tabs[0].id)
})

test('renameTab updates only the selected tab title', () => {
  const state = createInitialWorkbenchState()
  renameTab(state, state.tabs[0].id, 'prod-api')
  assert.equal(state.tabs[0].title, 'prod-api')
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: FAIL with missing `addTab`, `removeTab`, or `renameTab` exports.

- [ ] **Step 3: Add tab mutation helpers and the tab bar component**

```ts
export function addTab(state: SSHWorkbenchState, title = 'New Session') {
  const tab = createSessionTab(title)
  state.tabs.push(tab)
  state.activeTabId = tab.id
  state.activePaneId = tab.panes[0].id
}

export function removeTab(state: SSHWorkbenchState, tabId: string) {
  if (state.tabs.length === 1) return
  const index = state.tabs.findIndex((item) => item.id === tabId)
  if (index === -1) return
  state.tabs.splice(index, 1)
  const fallback = state.tabs[Math.max(0, index - 1)]
  state.activeTabId = fallback.id
  state.activePaneId = fallback.panes[0].id
}

export function renameTab(state: SSHWorkbenchState, tabId: string, title: string) {
  const tab = state.tabs.find((item) => item.id === tabId)
  if (tab) tab.title = title.trim() || tab.title
}
```

```vue
<template>
  <div class="ssh-tab-bar">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      class="ssh-tab"
      :class="{ 'is-active': tab.id === activeTabId, 'is-connected': tab.status === 'connected' }"
      type="button"
      @click="$emit('activate-tab', tab.id)"
    >
      <span class="ssh-tab__dot" :data-status="tab.status" />
      <span class="ssh-tab__title">{{ tab.title }}</span>
      <span class="ssh-tab__close" @click.stop="$emit('close-tab', tab.id)">x</span>
    </button>
    <button class="ssh-tab-add" type="button" @click="$emit('add-tab')">+</button>
  </div>
</template>
```

- [ ] **Step 4: Wire the tab bar and split actions into the main view**

```vue
<SSHTerminalToolbar
  :host-name="hostName"
  :host-ip="hostIp"
  :connected="activePane?.status === 'connected'"
  :font-size="activePane?.fontSize || 14"
  :show-file-panel="workbench.rightPanelOpen"
  @split-vertical="handleSplit('vertical')"
  @split-horizontal="handleSplit('horizontal')"
  @toggle-file-panel="workbench.rightPanelOpen = !workbench.rightPanelOpen"
/>

<SSHTabBar
  :tabs="workbench.tabs"
  :active-tab-id="workbench.activeTabId"
  @activate-tab="handleActivateTab"
  @close-tab="handleCloseTab"
  @add-tab="handleAddTab"
/>
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: PASS with the added tab-management tests.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/monitoring/ssh/useSSHWorkbench.ts frontend/src/views/monitoring/ssh/sshWorkbench.test.mjs frontend/src/views/monitoring/ssh/SSHTabBar.vue frontend/src/views/monitoring/ssh/SSHTerminalToolbar.vue frontend/src/views/monitoring/SSHTerminalView.vue
git commit -m "feat(ssh): add workbench tabs and split controls"
```

## Task 3: Move xterm and WebSocket lifecycle into pane-scoped components

**Files:**
- Create: `frontend/src/views/monitoring/ssh/SSHPane.vue`
- Create: `frontend/src/views/monitoring/ssh/SSHPaneGrid.vue`
- Modify: `frontend/src/views/monitoring/SSHTerminalView.vue`
- Modify: `frontend/src/views/monitoring/ssh/sshConnection.ts`
- Test: `frontend/src/views/monitoring/ssh/sshConnection.test.mjs`

- [ ] **Step 1: Add a failing helper test for auth defaults reused by new panes**

```js
test('buildAuthPayload preserves key auth mode for new pane sessions', () => {
  const payload = buildAuthPayload({
    username: 'ops',
    password: '',
    port: 22,
    authMode: 'key-8',
  })
  assert.deepEqual(payload, { key_id: 8 })
})
```

- [ ] **Step 2: Run the SSH helper tests to verify the current baseline**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshConnection.test.mjs`  
Expected: PASS for existing tests and FAIL only if new helper expectations are unmet.

- [ ] **Step 3: Create pane-scoped terminal components**

```vue
<template>
  <section class="ssh-pane" :class="{ 'is-active': active }" @click="$emit('activate', pane.id)">
    <header class="ssh-pane__header">
      <div class="ssh-pane__title">{{ pane.title }}</div>
      <div class="ssh-pane__meta">{{ pane.currentPath || '/' }}</div>
    </header>
    <SSHLoginForm
      v-model:visible="showLogin"
      :host-ip="hostIp"
      :ssh-keys="sshKeys"
      :connecting="pane.status === 'connecting'"
      :connected="pane.status === 'connected'"
      @connect="connectPane"
    />
    <div ref="terminalRef" class="ssh-pane__terminal" />
  </section>
</template>
```

```vue
<template>
  <div class="ssh-pane-grid" :data-layout="layout">
    <SSHPane
      v-for="pane in panes"
      :key="pane.id"
      :pane="pane"
      :active="pane.id === activePaneId"
      :host-ip="hostIp"
      :ssh-keys="sshKeys"
      @activate="$emit('activate-pane', $event)"
      @status-change="$emit('status-change', $event)"
    />
  </div>
</template>
```

- [ ] **Step 4: Replace the monolithic xterm lifecycle in the page shell**

```ts
const workbench = reactive(createInitialWorkbenchState())

const activeTab = computed(() => workbench.tabs.find((item) => item.id === workbench.activeTabId))
const activePane = computed(() => activeTab.value?.panes.find((item) => item.id === workbench.activePaneId))

function handlePaneStatusChange(payload: { paneId: string; status: SSHConnectionStatus; error?: string }) {
  const tab = activeTab.value
  const pane = tab?.panes.find((item) => item.id === payload.paneId)
  if (!tab || !pane) return
  pane.status = payload.status
  pane.lastError = payload.error || ''
  tab.status = tab.panes.some((item) => item.status === 'connected') ? 'connected' : payload.status
}
```

- [ ] **Step 5: Run the helper tests and a production build check**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshConnection.test.mjs`  
Expected: PASS

Run: `cd frontend && npm run build`  
Expected: PASS with no TypeScript errors from the new pane components.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/monitoring/ssh/SSHPane.vue frontend/src/views/monitoring/ssh/SSHPaneGrid.vue frontend/src/views/monitoring/ssh/sshConnection.ts frontend/src/views/monitoring/ssh/sshConnection.test.mjs frontend/src/views/monitoring/SSHTerminalView.vue
git commit -m "feat(ssh): scope terminal lifecycle to workbench panes"
```

## Task 4: Rebuild the right-side collaboration panel

**Files:**
- Create: `frontend/src/views/monitoring/ssh/SSHRightPanel.vue`
- Modify: `frontend/src/views/monitoring/ssh/SFTPFilePanel.vue`
- Modify: `frontend/src/views/monitoring/ssh/FileEditDialog.vue`
- Modify: `frontend/src/views/monitoring/SSHTerminalView.vue`

- [ ] **Step 1: Capture the desired panel contract in a failing integration sketch**

```js
test('right panel defaults to files tab and can switch to preview mode', () => {
  const state = createInitialWorkbenchState()
  assert.equal(state.rightPanelTab, 'files')
  state.rightPanelTab = 'preview'
  assert.equal(state.rightPanelTab, 'preview')
})
```

- [ ] **Step 2: Run the state tests to keep the baseline explicit**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: PASS after adding the lightweight right-panel expectation.

- [ ] **Step 3: Create the persistent right panel shell**

```vue
<template>
  <aside v-if="open" class="ssh-right-panel">
    <div class="ssh-right-panel__tabs">
      <button v-for="item in panelTabs" :key="item.value" :class="{ 'is-active': item.value === activeTab }" @click="$emit('change-tab', item.value)">
        {{ item.label }}
      </button>
    </div>
    <div class="ssh-right-panel__body">
      <SFTPFilePanel
        v-if="activeTab === 'files'"
        :visible="true"
        :connected="connected"
        :asset-id="assetId"
        :current-key-id="currentKeyId"
        @edit-file="$emit('edit-file', $event)"
      />
      <div v-else-if="activeTab === 'preview'">preview here</div>
      <div v-else-if="activeTab === 'actions'">actions here</div>
      <div v-else>info here</div>
    </div>
  </aside>
</template>
```

- [ ] **Step 4: Refactor the SFTP panel away from slide-in behavior**

```scss
.file-panel {
  width: 100%;
  height: 100%;
  border-left: 0;
  background: var(--surface-color);
}

.file-panel-header {
  min-height: 44px;
  padding: 10px 12px;
}
```

Implementation notes:
- Remove the transition wrapper from `SFTPFilePanel.vue`.
- Remove the close button from the panel header; panel visibility belongs to the workbench shell now.
- Keep `defineExpose({ navigateTo, currentPath })` so the page shell can sync panes and files.

- [ ] **Step 5: Run a production build check**

Run: `cd frontend && npm run build`  
Expected: PASS with no unused-prop or template errors after moving visibility control to `SSHRightPanel.vue`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/monitoring/ssh/SSHRightPanel.vue frontend/src/views/monitoring/ssh/SFTPFilePanel.vue frontend/src/views/monitoring/ssh/FileEditDialog.vue frontend/src/views/monitoring/SSHTerminalView.vue
git commit -m "feat(ssh): add persistent right-side collaboration panel"
```

## Task 5: Add the bottom status bar and active-pane status plumbing

**Files:**
- Create: `frontend/src/views/monitoring/ssh/SSHStatusBar.vue`
- Modify: `frontend/src/views/monitoring/ssh/types.ts`
- Modify: `frontend/src/views/monitoring/ssh/SSHPane.vue`
- Modify: `frontend/src/views/monitoring/SSHTerminalView.vue`

- [ ] **Step 1: Add a failing state test for pane metadata updates**

```js
import { updatePaneMeta } from './useSSHWorkbench.ts'

test('updatePaneMeta stores current path and error text for the active pane', () => {
  const state = createInitialWorkbenchState()
  const paneId = state.tabs[0].panes[0].id
  updatePaneMeta(state, paneId, { currentPath: '/var/log', lastError: 'connection reset' })
  assert.equal(state.tabs[0].panes[0].currentPath, '/var/log')
  assert.equal(state.tabs[0].panes[0].lastError, 'connection reset')
})
```

- [ ] **Step 2: Run the state tests to verify they fail**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: FAIL with missing `updatePaneMeta`.

- [ ] **Step 3: Implement pane metadata updates and the status bar**

```ts
export function updatePaneMeta(
  state: SSHWorkbenchState,
  paneId: string,
  patch: Partial<Pick<SSHPaneState, 'currentPath' | 'connectionSeconds' | 'dirtyFilePath' | 'lastError' | 'authMode'>>
) {
  for (const tab of state.tabs) {
    const pane = tab.panes.find((item) => item.id === paneId)
    if (pane) Object.assign(pane, patch)
  }
}
```

```vue
<template>
  <footer class="ssh-status-bar">
    <span>{{ pane.status }}</span>
    <span>{{ pane.authMode }}</span>
    <span>{{ pane.currentPath || '/' }}</span>
    <span>{{ pane.connectionSeconds }}s</span>
    <span v-if="pane.dirtyFilePath">dirty: {{ pane.dirtyFilePath }}</span>
    <span v-else-if="pane.lastError">{{ pane.lastError }}</span>
  </footer>
</template>
```

- [ ] **Step 4: Emit pane metadata from the terminal and file flows**

```ts
emit('meta-change', {
  paneId: props.pane.id,
  currentPath: inferredPath,
  connectionSeconds: elapsed,
  authMode: formData.authMode,
})
```

```ts
function handleFileDirty(path: string) {
  updatePaneMeta(workbench, workbench.activePaneId, { dirtyFilePath: path })
}
```

- [ ] **Step 5: Run the state tests and build**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: PASS

Run: `cd frontend && npm run build`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/monitoring/ssh/types.ts frontend/src/views/monitoring/ssh/useSSHWorkbench.ts frontend/src/views/monitoring/ssh/SSHStatusBar.vue frontend/src/views/monitoring/ssh/SSHPane.vue frontend/src/views/monitoring/SSHTerminalView.vue
git commit -m "feat(ssh): add pane-aware status bar"
```

## Task 6: Polish the login, toolbar, and visual system for ops-heavy use

**Files:**
- Modify: `frontend/src/views/monitoring/ssh/SSHLoginForm.vue`
- Modify: `frontend/src/views/monitoring/ssh/SSHTerminalToolbar.vue`
- Modify: `frontend/src/views/monitoring/SSHTerminalView.vue`
- Modify: `frontend/src/assets/styles/index.scss`

- [ ] **Step 1: Make the visual contract explicit with a manual QA checklist**

```md
- terminal remains the darkest visual surface
- toolbar stays under 48px height
- left rail does not exceed 84px collapsed width
- right panel stays within 360px
- no inline styles remain in the rebuilt SSH page
- active tab, active pane, and disconnected pane are all visually distinct
```

- [ ] **Step 2: Rework the login form copy and layout**

```vue
<template #header>
  <div class="login-header">
    <div>
      <strong>Open Session</strong>
      <div class="login-subtitle">{{ hostIp }}</div>
    </div>
    <el-tag :type="connected ? 'success' : 'info'" size="small">{{ connected ? 'Connected' : 'Idle' }}</el-tag>
  </div>
</template>
```

Implementation notes:
- Replace emoji-like labels with clean text.
- Use project tokens instead of hardcoded brand colors where practical.
- Keep authentication hints concise and operational.

- [ ] **Step 3: Finish the toolbar controls for split, tabs, and panel toggles**

```vue
<el-tooltip content="Split vertically">
  <el-button text size="small" @click="$emit('split-vertical')">
    <el-icon><Rank /></el-icon>
  </el-button>
</el-tooltip>
<el-tooltip content="Split horizontally">
  <el-button text size="small" @click="$emit('split-horizontal')">
    <el-icon><Operation /></el-icon>
  </el-button>
</el-tooltip>
```

- [ ] **Step 4: Run the full frontend verification**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshConnection.test.mjs src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: PASS

Run: `cd frontend && npm run build`  
Expected: PASS with the rebuilt SSH workbench included in the final bundle.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/monitoring/ssh/SSHLoginForm.vue frontend/src/views/monitoring/ssh/SSHTerminalToolbar.vue frontend/src/views/monitoring/SSHTerminalView.vue frontend/src/assets/styles/index.scss
git commit -m "feat(ssh): polish workbench interactions and visual system"
```

## Task 7: Final QA and rollout checks

**Files:**
- Modify: `docs/superpowers/specs/2026-06-27-ssh-workbench-design.md`
- Modify: `docs/superpowers/plans/2026-06-27-ssh-workbench.md`

- [ ] **Step 1: Run end-to-end manual checks**

```md
1. Open `/monitoring/hosts/:id/ssh`
2. Connect the first pane with asset auth
3. Add a second tab and connect with key auth
4. Split the active tab vertically
5. Open the right panel and browse files
6. Edit a text file and confirm dirty status appears
7. Disconnect one pane and verify the other pane/tab remains usable
8. Reconnect the failed pane from the workbench without reloading the page
```

- [ ] **Step 2: Run the final verification commands**

Run: `cd frontend && node --test src/views/monitoring/ssh/sshConnection.test.mjs src/views/monitoring/ssh/sshWorkbench.test.mjs`  
Expected: PASS

Run: `cd frontend && npm run build`  
Expected: PASS

- [ ] **Step 3: Update the spec/plan if implementation deviated**

```md
- If right-panel editing stayed dialog-based for V1, update both docs to say "preview-first with dialog fallback".
- If pane path detection remains best-effort, document that explicitly in the spec and release notes.
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-27-ssh-workbench-design.md docs/superpowers/plans/2026-06-27-ssh-workbench.md
git commit -m "docs(ssh): finalize workbench delivery notes"
```
