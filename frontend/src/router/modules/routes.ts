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
        path: 'containers',
        name: 'Containers',
        component: () => import('@/views/containers/ContainerView.vue'),
        meta: { title: '容器管理', icon: 'Box', permission: 'containers.view' },
      },
      {
        path: ':id',
        name: 'AssetDetail',
        component: () => import('@/views/assets/AssetDetailView.vue'),
        meta: { title: '资产详情', hidden: true, permission: 'assets.view' },
      },
    ],
  },
  {
    path: '/monitoring',
    component: Layout,
    redirect: '/monitoring/metrics',
    meta: { title: '监控告警', icon: 'DataLine' },
    children: [
      {
        path: 'metrics',
        name: 'MetricList',
        component: () => import('@/views/monitoring/MetricListView.vue'),
        meta: { title: '监控指标', icon: 'TrendCharts', permission: 'monitoring.view' },
      },
      {
        path: 'hosts',
        name: 'HostList',
        component: () => import('@/views/monitoring/HostListView.vue'),
        meta: { title: '主机监控', icon: 'Cpu', permission: 'monitoring.view' },
      },
      {
        path: 'hosts/:id',
        name: 'HostDetail',
        component: () => import('@/views/monitoring/HostDetailView.vue'),
        meta: { title: '主机详情', hidden: true, permission: 'monitoring.view' },
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
        meta: { title: '工单详情', hidden: true, permission: 'tickets.view' },
      },
    ],
  },
  {
    path: '/alerts',
    component: Layout,
    children: [
      {
        path: '',
        name: 'AlertList',
        component: () => import('@/views/alerts/AlertListView.vue'),
        meta: { title: '告警中心', icon: 'Bell', permission: 'alerts.view' },
      },
      {
        path: ':id',
        name: 'AlertDetail',
        component: () => import('@/views/alerts/AlertDetailView.vue'),
        meta: { title: '告警详情', hidden: true, permission: 'alerts.view' },
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
    path: '/audit',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Audit',
        component: () => import('@/views/audit/AuditView.vue'),
        meta: { title: '审计日志', icon: 'Notebook', permission: 'audit.view' },
      },
    ],
  },
  {
    path: '/password',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Password',
        component: () => import('@/views/password/PasswordView.vue'),
        meta: { title: '修改密码', hidden: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

export default routes
