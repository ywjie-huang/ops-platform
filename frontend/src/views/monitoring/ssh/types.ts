export type SSHConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error'

export type SSHPaneLayout = 'single' | 'vertical' | 'horizontal'

export type SSHRightPanelTab = 'files' | 'actions' | 'info'

export interface SSHHostRef {
  assetId: number
  name: string
  ip: string
  username: string
  port: number
  authMode: string
}

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
  host: SSHHostRef
  panes: SSHPaneState[]
}

export interface SSHWorkbenchState {
  activeTabId: string
  activePaneId: string
  rightPanelTab: SSHRightPanelTab
  rightPanelOpen: boolean
  tabs: SSHTabState[]
}
