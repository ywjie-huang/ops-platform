export type SSHConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error'

export type SSHPaneLayout = 'single' | 'vertical' | 'horizontal'

export type SSHRightPanelTab = 'files' | 'preview' | 'actions' | 'info'

export interface SSHPaneState {
  id: string
  title: string
  status: SSHConnectionStatus
  hostLabel: string
  currentPath: string
  authMode: string | null
  fontSize: number
  connectionSeconds: number
  dirtyFilePath: string | null
  lastError: string | null
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
  rightPanelTab: SSHRightPanelTab
  rightPanelOpen: boolean
  tabs: SSHTabState[]
}
