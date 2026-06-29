import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  createInitialWorkbenchState,
  addTab,
  splitActiveTab,
  closePane,
  removeTab,
  renameTab,
  setActivePane,
  updatePaneMeta,
} = await import('./useSSHWorkbench.ts')

test('default state starts with one tab and one pane', () => {
  const state = createInitialWorkbenchState()

  assert.equal(state.tabs.length, 1)
  assert.equal(state.tabs[0].layout, 'single')
  assert.equal(state.tabs[0].panes.length, 1)
  assert.equal(state.activeTabId, state.tabs[0].id)
  assert.equal(state.activePaneId, state.tabs[0].panes[0].id)
})

test('right panel defaults to files tab and can switch to preview mode', () => {
  const state = createInitialWorkbenchState()

  assert.equal(state.rightPanelOpen, true)
  assert.equal(state.rightPanelTab, 'files')

  state.rightPanelTab = 'preview'

  assert.equal(state.rightPanelTab, 'preview')
})

test('splitActiveTab creates a second pane and records layout metadata', () => {
  const state = createInitialWorkbenchState()

  splitActiveTab(state, 'vertical')

  const activeTab = state.tabs[0]
  assert.equal(activeTab.layout, 'vertical')
  assert.equal(activeTab.panes.length, 2)
  assert.equal(state.activePaneId, activeTab.panes[1].id)
})

test('closePane collapses split tab back to a single pane', () => {
  const state = createInitialWorkbenchState()

  splitActiveTab(state, 'vertical')
  const firstPaneId = state.tabs[0].panes[0].id
  setActivePane(state, firstPaneId)

  closePane(state, state.tabs[0].panes[1].id)

  assert.equal(state.tabs[0].layout, 'single')
  assert.equal(state.tabs[0].panes.length, 1)
  assert.equal(state.activePaneId, firstPaneId)
})

test('addTab appends an idle tab and activates it', () => {
  const state = createInitialWorkbenchState()

  const newTab = addTab(state, 'Web 02')

  assert.equal(state.tabs.length, 2)
  assert.equal(state.activeTabId, newTab.id)
  assert.equal(state.activePaneId, newTab.panes[0].id)
  assert.equal(newTab.status, 'idle')
  assert.equal(newTab.panes[0].status, 'idle')
  assert.equal(newTab.title, 'Web 02')
})

test('removeTab falls back to the previous tab', () => {
  const state = createInitialWorkbenchState()
  const firstTab = state.tabs[0]
  const secondTab = addTab(state, 'Web 02')
  const thirdTab = addTab(state, 'Web 03')

  assert.equal(state.activeTabId, thirdTab.id)

  removeTab(state, thirdTab.id)

  assert.equal(state.tabs.length, 2)
  assert.equal(state.activeTabId, secondTab.id)
  assert.equal(state.activePaneId, secondTab.panes[0].id)
  assert.equal(state.tabs[0].id, firstTab.id)
})

test('renameTab updates only the selected tab title', () => {
  const state = createInitialWorkbenchState()
  const firstTabTitle = state.tabs[0].title
  const secondTab = addTab(state, 'Web 02')

  renameTab(state, secondTab.id, 'Gateway SSH')

  assert.equal(state.tabs[0].title, firstTabTitle)
  assert.equal(state.tabs[1].title, 'Gateway SSH')
  assert.equal(secondTab.title, 'Gateway SSH')
})

test('updatePaneMeta stores current path and error text for the active pane', () => {
  const state = createInitialWorkbenchState()
  const paneId = state.tabs[0].panes[0].id

  updatePaneMeta(state, paneId, {
    currentPath: '/var/log',
    lastError: 'connection reset',
  })

  assert.equal(state.tabs[0].panes[0].currentPath, '/var/log')
  assert.equal(state.tabs[0].panes[0].lastError, 'connection reset')
})
