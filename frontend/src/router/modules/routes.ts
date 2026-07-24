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
    redirect: '/assets/hosts',
    meta: { title: '资产管理', icon: 'Monitor' },
    children: [
      {
        path: 'hosts',
        name: 'AssetList',
        component: () => import('@/views/assets/AssetListView.vue'),
        meta: { title: '主机管理', icon: 'Platform', permission: 'assets.view' },
      },
      {
        path: 'ssh-keys',
        name: 'SSHKeyList',
        component: () => import('@/views/assets/SSHKeyListView.vue'),
        meta: { title: '主机密钥', icon: 'Key', permission: 'ssh_keys.view' },
      },
      {
        path: 'containers',
        name: 'Containers',
        component: () => import('@/views/containers/ContainerView.vue'),
        meta: { title: 'K8s 集群', icon: 'Box', permission: 'containers.view' },
      },
      {
        path: 'containers/cluster/:name',
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
        path: 'docker/host/:name',
        name: 'DockerDetail',
        component: () => import('@/views/containers/DockerDetailView.vue'),
        meta: { title: '主机详情', hidden: true, permission: 'containers.view', parentTitle: 'Docker 监控', activeMenu: '/assets/docker' },
      },
      {
        path: 'hosts/:publicId',
        name: 'AssetDetail',
        component: () => import('@/views/assets/AssetDetailView.vue'),
        meta: { title: '资产详情', hidden: true, permission: 'assets.view', parentTitle: '主机管理', activeMenu: '/assets/hosts' },
      },
      {
        path: 'list',
        redirect: '/assets/hosts',
        meta: { hidden: true },
      },
      {
        path: ':legacyId(\\d+)',
        name: 'LegacyAssetDetail',
        component: () => import('@/views/assets/AssetDetailView.vue'),
        meta: { title: '资产详情', hidden: true, permission: 'assets.view', parentTitle: '主机管理', activeMenu: '/assets/hosts' },
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
        meta: { title: '告警规则', icon: 'Warning', permission: 'monitoring.view' },
      },
      {
        path: 'events',
        name: 'AlertEventList',
        component: () => import('@/views/alerts/AlertEventListView.vue'),
        meta: { title: '告警事件', icon: 'Bell', permission: 'monitoring.view' },
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
    path: '/deploy',
    component: Layout,
    redirect: '/deploy/apps',
    meta: { title: '应用发布', icon: 'Folder' },
    children: [
      {
        path: 'apps',
        name: 'DeployAppList',
        component: () => import('@/views/deploy/AppListView.vue'),
        meta: { title: '应用管理', icon: 'Folder', permission: 'deploy.view' },
      },
      {
        path: 'apps/create',
        name: 'DeployAppCreate',
        component: () => import('@/views/deploy/AppCreateView.vue'),
        meta: { title: '创建应用', hidden: true, permission: 'deploy.create', parentTitle: '应用管理', activeMenu: '/deploy/apps' },
      },
      {
        path: 'apps/:name',
        name: 'DeployAppDetail',
        component: () => import('@/views/deploy/AppDetailView.vue'),
        meta: { title: '应用详情', hidden: true, permission: 'deploy.view', parentTitle: '应用管理', activeMenu: '/deploy/apps' },
      },
      {
        path: 'apps/:name/edit',
        name: 'DeployAppEdit',
        component: () => import('@/views/deploy/AppEditView.vue'),
        meta: { title: '编辑应用', hidden: true, permission: 'deploy.update', parentTitle: '应用管理', activeMenu: '/deploy/apps' },
      },
      {
        path: 'records',
        name: 'DeployRecordList',
        component: () => import('@/views/deploy/DeployRecordView.vue'),
        meta: { title: '部署记录', icon: 'List', permission: 'deploy.view' },
      },
      {
        path: 'records/:id',
        name: 'DeployRecordDetail',
        component: () => import('@/views/deploy/DeployDetailView.vue'),
        meta: { title: '部署详情', hidden: true, permission: 'deploy.view', parentTitle: '部署记录', activeMenu: '/deploy/records' },
      },
      {
        path: 'approvals',
        name: 'DeployApprovals',
        component: () => import('@/views/deploy/ApprovalView.vue'),
        meta: { title: '部署审批', icon: 'Stamp', permission: 'deploy.approve' },
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
        meta: { title: '巡检指挥台', icon: 'Finished', permission: 'patrol.view' },
      },
      {
        path: 'cockpit',
        name: 'PatrolCockpit',
        component: () => import('@/views/patrol/PatrolCockpitView.vue'),
        meta: { title: '态势大屏', hidden: true, permission: 'patrol.view', parentTitle: '巡检指挥台', activeMenu: '/patrol' },
      },
      {
        path: 'settings',
        name: 'PatrolSettings',
        redirect: '/patrol',
        meta: {
          title: '校准阈值',
          icon: 'Setting',
          permission: 'patrol.view',
          hidden: true,
          parentTitle: '巡检指挥台',
          activeMenu: '/patrol',
        },
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
