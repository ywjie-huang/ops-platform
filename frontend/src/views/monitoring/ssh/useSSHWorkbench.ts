import type {
  SSHHostRef,
  SSHPaneLayout,
  SSHPaneState,
  SSHTabState,
  SSHWorkbenchState,
} from './types'

let nextTabId = 1
let nextPaneId = 1

const DEFAULT_HOST: SSHHostRef = {
  assetId: 0,
  name: '',
  ip: '',
  username: 'root',
  port: 22,
  authMode: 'asset',
}

function createPane(title: string): SSHPaneState {
  return {
    id: `pane-${nextPaneId++}`,
    title,
    status: 'idle',
    hostLabel: '',
    currentPath: '',
    authMode: null,
    fontSize: 13,
    connectionSeconds: 0,
    dirtyFilePath: null,
    lastError: null,
  }
}

export function createSessionTab(title = `Session ${nextTabId}`, host: SSHHostRef = DEFAULT_HOST): SSHTabState {
  const pane = createPane(title)

  return {
    id: `tab-${nextTabId++}`,
    title,
    pinned: false,
    status: 'idle',
    layout: 'single',
    host,
    panes: [pane],
  }
}

export function addTab(state: SSHWorkbenchState, title?: string, host?: SSHHostRef): SSHTabState {
  const tab = createSessionTab(title, host)
  state.tabs.push(tab)
  state.activeTabId = tab.id
  state.activePaneId = tab.panes[0].id
  return tab
}

export const appendSessionTab = addTab

export function createInitialWorkbenchState(host?: SSHHostRef): SSHWorkbenchState {
  const firstTab = createSessionTab('Session 1', host)

  return {
    activeTabId: firstTab.id,
    activePaneId: firstTab.panes[0].id,
    rightPanelTab: 'files',
    rightPanelOpen: true,
    tabs: [firstTab],
  }
}

export function setTabHost(state: SSHWorkbenchState, tabId: string, host: SSHHostRef): void {
  const tab = state.tabs.find((item) => item.id === tabId)
  if (tab) {
    tab.host = host
  }
}

function getActiveTab(state: SSHWorkbenchState): SSHTabState | undefined {
  return state.tabs.find((tab) => tab.id === state.activeTabId)
}

export function removeTab(state: SSHWorkbenchState, tabId: string): void {
  if (state.tabs.length === 1) {
    return
  }

  const tabIndex = state.tabs.findIndex((tab) => tab.id === tabId)
  if (tabIndex === -1) {
    return
  }

  state.tabs.splice(tabIndex, 1)

  if (state.activeTabId !== tabId) {
    return
  }

  const fallbackTab = state.tabs[Math.max(0, tabIndex - 1)]
  state.activeTabId = fallbackTab.id
  state.activePaneId = fallbackTab.panes[0].id
}

export function renameTab(state: SSHWorkbenchState, tabId: string, title: string): void {
  const targetTab = state.tabs.find((tab) => tab.id === tabId)
  if (!targetTab) {
    return
  }

  const nextTitle = title.trim()
  if (!nextTitle) {
    return
  }

  targetTab.title = nextTitle
}

export function setActivePane(state: SSHWorkbenchState, paneId: string): void {
  const activeTab = getActiveTab(state)
  if (!activeTab || !activeTab.panes.some((pane) => pane.id === paneId)) {
    return
  }

  state.activePaneId = paneId
}

export function splitActiveTab(state: SSHWorkbenchState, layout: Exclude<SSHPaneLayout, 'single'>): void {
  const activeTab = getActiveTab(state)
  if (!activeTab) {
    return
  }

  const sourcePane =
    activeTab.panes.find((pane) => pane.id === state.activePaneId) ?? activeTab.panes[0]

  const nextPane = createPane(`${activeTab.title} Split`)
  nextPane.hostLabel = sourcePane.hostLabel
  nextPane.currentPath = sourcePane.currentPath
  nextPane.authMode = sourcePane.authMode
  nextPane.fontSize = sourcePane.fontSize

  activeTab.layout = layout
  activeTab.panes = [sourcePane, nextPane]
  state.activePaneId = nextPane.id
}

export function closePane(state: SSHWorkbenchState, paneId: string): void {
  const activeTab = getActiveTab(state)
  if (!activeTab || activeTab.panes.length === 1) {
    return
  }

  const remainingPanes = activeTab.panes.filter((pane) => pane.id !== paneId)
  if (remainingPanes.length === activeTab.panes.length || remainingPanes.length === 0) {
    return
  }

  activeTab.layout = 'single'
  activeTab.panes = [remainingPanes[0]]

  if (state.activePaneId === paneId) {
    state.activePaneId = remainingPanes[0].id
  }
}

export function updatePaneMeta(
  state: SSHWorkbenchState,
  paneId: string,
  patch: Partial<
    Pick<
      SSHPaneState,
      'authMode' | 'connectionSeconds' | 'currentPath' | 'dirtyFilePath' | 'lastError'
    >
  >,
): void {
  for (const tab of state.tabs) {
    const pane = tab.panes.find((item) => item.id === paneId)
    if (pane) {
      Object.assign(pane, patch)
      return
    }
  }
}
