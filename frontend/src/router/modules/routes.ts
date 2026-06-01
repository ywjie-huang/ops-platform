import type { RouteRecordRaw } from 'vue-router'

const Layout = () => import('@/layouts/DefaultLayout.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', hidden: true },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    meta: { title: '报表大屏', icon: 'DataAnalysis' },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '仪表盘', icon: 'Odometer', permission: 'dashboard.view' },
      },
      {
        path: 'reports',
        name: 'ReportList',
        component: () => import('@/views/reports/ReportView.vue'),
        meta: { title: '报表中心', icon: 'PieChart', permission: 'reports.view' },
      },
      {
        path: 'reports/:id',
        name: 'ReportDetail',
        component: () => import('@/views/reports/ReportDetailView.vue'),
        meta: { title: '报表详情', hidden: true, permission: 'reports.view', parentTitle: '报表中心', activeMenu: '/reports' },
      },
    ],
  },
  {
    path: '/assets',
    component: Layout,
    redirect: '/assets/list',
    meta: { title: '资产管理', icon: 'Monitor' },
    children: [
      {
        path: 'list',
        name: 'AssetList',
        component: () => import('@/views/assets/AssetListView.vue'),
        meta: { title: '主机管理', icon: 'Platform', permission: 'assets.view' },
      },
      {
        path: 'ssh-keys',
        name: 'SSHKeyList',
        component: () => import('@/views/assets/SSHKeyListView.vue'),
        meta: { title: '主机密钥', icon: 'Key', permission: 'assets.view' },
      },
      {
        path: 'containers',
        name: 'Containers',
        component: () => import('@/views/containers/ContainerView.vue'),
        meta: { title: 'K8s 集群', icon: 'Box', permission: 'containers.view' },
      },
      {
        path: 'containers/:id',
        name: 'ContainerDetail',
        component: () => import('@/views/containers/ContainerDetailView.vue'),
        meta: { title: '集群详情', hidden: true, permission: 'containers.view', parentTitle: 'K8s 集群', activeMenu: '/assets/containers' },
      },
      {
        path: 'docker',
        name: 'DockerMonitor',
        component: () => import('@/views/containers/DockerView.vue'),
        meta: { title: 'Docker 监控', icon: 'Connection', permission: 'containers.view' },
      },
      {
        path: 'docker/:id',
        name: 'DockerDetail',
        component: () => import('@/views/containers/DockerDetailView.vue'),
        meta: { title: '主机详情', hidden: true, permission: 'containers.view', parentTitle: 'Docker 监控', activeMenu: '/assets/docker' },
      },
      {
        path: ':id',
        name: 'AssetDetail',
        component: () => import('@/views/assets/AssetDetailView.vue'),
        meta: { title: '资产详情', hidden: true, permission: 'assets.view', parentTitle: '主机管理', activeMenu: '/assets/list' },
      },
    ],
  },
  {
    path: '/monitoring',
    component: Layout,
    redirect: '/monitoring/hosts',
    meta: { title: '监控告警', icon: 'DataLine' },
    children: [
      {
        path: 'hosts',
        name: 'HostList',
        component: () => import('@/views/monitoring/HostListView.vue'),
        meta: { title: '主机监控', icon: 'Cpu', permission: 'monitoring.view' },
      },
      {
        path: 'rules',
        name: 'AlertRuleList',
        component: () => import('@/views/monitoring/AlertRuleListView.vue'),
        meta: { title: '告警规则', icon: 'Warning', permission: 'alerts.view' },
      },
      {
        path: 'events',
        name: 'AlertEventList',
        component: () => import('@/views/alerts/AlertEventListView.vue'),
        meta: { title: '告警事件', icon: 'Bell', permission: 'alerts.view' },
      },
      {
        path: 'alerts',
        name: 'AlertList',
        component: () => import('@/views/alerts/AlertListView.vue'),
        meta: { title: '告警管理', icon: 'BellFilled', permission: 'alerts.view' },
      },
      {
        path: 'alerts/:id',
        name: 'AlertDetail',
        component: () => import('@/views/alerts/AlertDetailView.vue'),
        meta: { title: '告警详情', hidden: true, permission: 'alerts.view', parentTitle: '告警管理', activeMenu: '/monitoring/alerts' },
      },
      {
        path: 'hosts/:id/ssh',
        name: 'SSHTerminal',
        component: () => import('@/views/monitoring/SSHTerminalView.vue'),
        meta: { title: 'SSH 终端', hidden: true, permission: 'monitoring.view', parentTitle: '主机监控', activeMenu: '/monitoring/hosts' },
      },
      {
        path: 'hosts/:id',
        name: 'HostDetail',
        component: () => import('@/views/monitoring/HostDetailView.vue'),
        meta: { title: '主机详情', hidden: true, permission: 'monitoring.view', parentTitle: '主机监控', activeMenu: '/monitoring/hosts' },
      },

    ],
  },
  {
    path: '/tickets',
    component: Layout,
    children: [
      {
        path: '',
        name: 'TicketList',
        component: () => import('@/views/tickets/TicketListView.vue'),
        meta: { title: '工单协作', icon: 'Document', permission: 'tickets.view' },
      },
      {
        path: ':id',
        name: 'TicketDetail',
        component: () => import('@/views/tickets/TicketDetailView.vue'),
        meta: { title: '工单详情', hidden: true, permission: 'tickets.view', parentTitle: '工单协作', activeMenu: '/tickets' },
      },
    ],
  },
  {
    path: '/users',
    component: Layout,
    redirect: '/users/list',
    meta: { title: '用户管理', icon: 'User' },
    children: [
      {
        path: 'list',
        name: 'UserList',
        component: () => import('@/views/users/UserListView.vue'),
        meta: { title: '用户管理', icon: 'User', permission: 'users.view' },
      },
      {
        path: 'roles',
        name: 'RoleList',
        component: () => import('@/views/roles/RoleListView.vue'),
        meta: { title: '角色权限', icon: 'Key', permission: 'roles.view' },
      },
    ],
  },
  {
    path: '/batch-exec',
    component: Layout,
    children: [
      {
        path: '',
        name: 'BatchExec',
        component: () => import('@/views/batch/BatchExecView.vue'),
        meta: { title: '批量执行', icon: 'Promotion', permission: 'batch_exec.view' },
      },
    ],
  },
  {
    path: '/patrol',
    component: Layout,
    meta: { title: '巡检中心', icon: 'Finished' },
    children: [
      {
        path: '',
        name: 'Patrol',
        component: () => import('@/views/patrol/PatrolView.vue'),
        meta: { title: '巡检报告', icon: 'Finished', permission: 'patrol.view' },
      },
      {
        path: 'settings',
        name: 'PatrolSettings',
        component: () => import('@/views/patrol/PatrolSettingsView.vue'),
        meta: { title: '阈值配置', icon: 'Setting', permission: 'patrol.view' },
      },
      {
        path: 'scheduler',
        name: 'Scheduler',
        component: () => import('@/views/settings/SchedulerView.vue'),
        meta: { title: '定时任务', icon: 'Odometer', permission: 'patrol.view' },
      },
    ],
  },
  {
    path: '/ai',
    component: Layout,
    redirect: '/ai/chat',
    meta: { title: '智能中心', icon: 'Cpu' },
    children: [
      {
        path: 'chat',
        name: 'AiAssistant',
        component: () => import('@/views/ai/AiView.vue'),
        meta: { title: '智能助手', icon: 'ChatDotRound' },
      },
      {
        path: 'model',
        name: 'ModelConfig',
        component: () => import('@/views/ai/ModelConfigView.vue'),
        meta: { title: '模型配置', icon: 'Setting' },
      },
    ],
  },
  {
    path: '/system',
    component: Layout,
    redirect: '/system/audit',
    meta: { title: '系统管理', icon: 'Setting' },
    children: [
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/audit/AuditView.vue'),
        meta: { title: '审计日志', icon: 'Notebook', permission: 'audit.view' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { title: '配置中心', icon: 'Tools', permission: 'settings.view' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
    meta: { hidden: true },
  },
]

export default routes
