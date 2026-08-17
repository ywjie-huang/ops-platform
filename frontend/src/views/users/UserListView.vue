<template>
  <div>
    <!-- ═══ 页头 ═══ -->
    <div class="page-header">
      <div>
        <h2 class="page-title">用户管理</h2>
        <p class="page-subtitle">系统账号、角色分配与登录活跃度的统一管理。</p>
      </div>
      <el-button type="primary" size="small" @click="showDialog()">
        <el-icon><Plus /></el-icon>新增用户
      </el-button>
    </div>

    <!-- ═══ 统计卡 ═══ -->
    <div class="stats" role="region" aria-label="用户概览">
      <div class="stat">
        <div class="lbl"><span class="dot dot-p" aria-hidden="true"></span>用户总数</div>
        <div class="num">{{ stats?.total_users ?? '-' }}</div>
        <div class="foot">{{ stats ? `近 7 天新增 ${stats.new_users_7d} 人` : '' }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-s" aria-hidden="true"></span>今日登录</div>
        <div class="num">{{ stats?.today_logins ?? '-' }}</div>
        <div class="foot">
          <template v-if="stats">登录失败 <span :class="{ bad: stats.today_login_failed > 0 }">{{ stats.today_login_failed }} 次</span></template>
        </div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-w" aria-hidden="true"></span>7 天活跃</div>
        <div class="num">{{ stats?.active_7d ?? '-' }}</div>
        <div class="foot">{{ activeRateFoot }}</div>
      </div>
      <div class="stat clickable" title="点击筛选未分配角色的用户" role="button" tabindex="0" @click="filterNoRole" @keyup.enter="filterNoRole">
        <div class="lbl"><span class="dot dot-d" aria-hidden="true"></span>未分配角色</div>
        <div class="num" :class="{ warn: (stats?.no_role_count ?? 0) > 0 }">{{ stats?.no_role_count ?? '-' }}</div>
        <div class="foot">无角色登录后无任何权限，点击筛选</div>
      </div>
    </div>

    <div class="table-card">
      <!-- ═══ 工具栏 ═══ -->
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用户名、姓名…"
          clearable
          class="search-input"
          :prefix-icon="Search"
          aria-label="搜索用户"
          @keyup.enter="applyFilters"
          @clear="applyFilters"
        />
        <el-select v-model="filters.role_id" class="filter-select" aria-label="按角色筛选" @change="applyFilters">
          <el-option value="" label="角色：全部" />
          <el-option v-for="r in roles" :key="r.id" :value="r.id" :label="r.name" />
        </el-select>
        <el-select v-model="filters.activity" class="filter-select" aria-label="按状态筛选" @change="applyFilters">
          <el-option value="" label="状态：全部" />
          <el-option value="active_7d" label="近 7 天活跃" />
          <el-option value="dormant" label="超过 7 天未登录" />
          <el-option value="never" label="从未登录" />
          <el-option value="no_role" label="未分配角色" />
        </el-select>
        <span class="spacer"></span>
        <span class="meta">共 {{ total }} 个用户</span>
      </div>
      <!-- ═══ 用户表格 ═══ -->
      <el-table
        :data="items"
        v-loading="loading"
        class="user-table"
        @row-click="showDetail"
      >
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="u-cell">
              <span class="avatar" :style="{ background: avatarColor(row.username) }">{{ avatarChar(row.username) }}</span>
              <div class="u-name">
                <strong>{{ row.username }}<span v-if="row.id === myId" class="me-badge">我</span></strong>
                <span>{{ row.full_name }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="200">
          <template #default="{ row }">
            <div class="role-tags">
              <span v-for="r in row.roles" :key="r.id" class="tag" :class="roleTagClass(r)">{{ r.name }}</span>
              <span v-if="!row.roles?.length" class="tag warn">未分配</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="165">
          <template #default="{ row }">
            <div v-if="row.last_login_at" class="time-cell">
              {{ loginMainText(row.last_login_at) }}
              <span>{{ absoluteTime(row.last_login_at) }}</span>
            </div>
            <div v-else class="time-cell"><span class="never">从未登录</span></div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">
            <div class="time-cell">
              {{ dateOnly(row.created_at) }}
              <span>{{ createdAgoText(row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" align="center">
          <template #default="{ row }">
            <div class="action-cell" @click.stop>
              <el-button size="small" type="primary" link :aria-label="`编辑 ${row.username}`" @click="showDialog(row)">编辑</el-button>
              <el-button size="small" type="primary" link :aria-label="`重置 ${row.username} 的密码`" @click="showReset(row)">重置密码</el-button>
              <el-dropdown trigger="click" placement="bottom-end" :aria-label="`${row.username} 更多操作`" @command="() => handleDelete(row)">
                <el-button size="small" link class="action-more">
                  更多<el-icon class="action-more-icon"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="delete">
                      <span class="text-danger">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- ═══ 分页 ═══ -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          :layout="paginationLayout"
          small
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
    <!-- ═══ 新建/编辑弹窗 ═══ -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="560px" :close-on-click-modal="false" destroy-on-close>
      <div class="dlg-body">
        <div class="fld">
          <div class="fld-k"><em>*</em> 用户名</div>
          <el-input v-model="form.username" placeholder="登录账号" />
          <div class="hint">登录账号，创建后不建议修改</div>
        </div>
        <div class="fld">
          <div class="fld-k"><em>*</em> 姓名</div>
          <el-input v-model="form.full_name" placeholder="真实姓名" />
        </div>
        <div class="fld" v-if="!editingId">
          <div class="fld-k"><em>*</em> 密码</div>
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password />
        </div>
        <div class="fld">
          <div class="fld-k"><em>*</em> 角色</div>
          <div class="role-grid">
            <div
              v-for="r in roles"
              :key="r.id"
              class="role-card"
              :class="{ on: form.role_ids.includes(r.id) }"
              role="checkbox"
              :aria-checked="form.role_ids.includes(r.id)"
              tabindex="0"
              @click="toggleRole(r.id)"
              @keyup.enter="toggleRole(r.id)"
            >
              <strong>{{ r.name }}</strong>
              <span>{{ r.description || '暂无描述' }}</span>
            </div>
          </div>
          <div class="hint">不选角色则登录后无任何权限<template v-if="editingId">；密码修改请用列表「重置密码」</template></div>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- ═══ 重置密码弹窗 ═══ -->
    <el-dialog v-model="resetVisible" title="重置密码" width="420px" :close-on-click-modal="false" destroy-on-close>
      <div class="dlg-body">
        <p class="reset-tip">为用户「{{ resetTarget?.username }}」设置新密码，重置后请线下告知用户。</p>
        <div class="fld">
          <div class="fld-k"><em>*</em> 新密码</div>
          <el-input v-model="resetForm.password" type="password" placeholder="至少 6 位" show-password />
        </div>
        <div class="fld">
          <div class="fld-k"><em>*</em> 确认新密码</div>
          <el-input v-model="resetForm.confirm" type="password" placeholder="再次输入" show-password @keyup.enter="handleResetSave" />
        </div>
      </div>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="handleResetSave">确定</el-button>
      </template>
    </el-dialog>
    <!-- ═══ 用户详情抽屉 ═══ -->
    <el-drawer v-model="detailVisible" size="620px" :with-header="false" destroy-on-close>
      <div class="d-head">
        <div class="d-profile">
          <span class="avatar lg" :style="{ background: avatarColor(detailUser?.username || '') }">{{ avatarChar(detailUser?.username || '') }}</span>
          <div>
            <div class="d-title">
              {{ detailUser?.username }}
              <span v-for="r in detailUser?.roles || []" :key="r.id" class="tag" :class="roleTagClass(r)">{{ r.name }}</span>
              <span v-if="detailUser && !detailUser.roles?.length" class="tag warn">未分配</span>
            </div>
            <div class="d-sub">{{ detailUser?.full_name }} · 创建于 {{ dateOnly(detailUser?.created_at || null) }}</div>
          </div>
        </div>
        <button type="button" class="d-close" aria-label="关闭" @click="detailVisible = false">✕</button>
      </div>
      <div class="d-summary">
        <div>
          <div class="k">近 30 天登录</div>
          <div class="v">{{ detailActivity ? `${detailActivity.login_count_30d} 次` : '-' }}</div>
        </div>
        <div>
          <div class="k">最近登录</div>
          <div class="v">{{ detailActivity?.last_login_at ? loginMainText(detailActivity.last_login_at) : '从未登录' }}</div>
        </div>
        <div>
          <div class="k">登录失败（7 天）</div>
          <div class="v" :class="{ 'v-danger': (detailActivity?.login_failed_7d ?? 0) > 0 }">
            {{ detailActivity ? `${detailActivity.login_failed_7d} 次` : '-' }}
          </div>
        </div>
      </div>
      <div class="d-sec-k">最近动态</div>
      <div class="timeline" v-loading="detailLoading">
        <template v-if="detailActivity">
          <div v-for="log in detailActivity.recent_logs" :key="log.id" class="tl-item">
            <span class="tl-dot" :class="tlDotClass(log.action)" aria-hidden="true"></span>
            <div class="tl-head">
              <span class="tl-act">{{ actionLabel(log.action) }}</span>
              <span class="tl-time">{{ relativeShort(log.created_at) }}</span>
            </div>
            <div class="tl-detail">
              {{ log.detail || log.target_name || actionLabel(log.action) }}<template v-if="log.ip_address"> · IP {{ log.ip_address }}</template>
            </div>
          </div>
          <el-empty v-if="!detailLoading && !detailActivity.recent_logs.length" description="暂无动态" :image-size="80" />
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Search } from '@element-plus/icons-vue'
import {
  getUsers, getUserStats, getUserRoles, getUserActivity,
  createUser, updateUser, deleteUser, resetUserPassword,
  type UserItem, type UserStats, type RoleItem, type UserActivity,
} from '@/api/users'
import { usePagination } from '@/hooks/usePagination'
import { useAuthStore } from '@/stores/modules/auth'

const authStore = useAuthStore()
const myId = computed(() => authStore.userInfo?.id)

// ─── 列表 ────────────────────────────────────────────────
const loading = ref(false)
const items = ref<UserItem[]>([])
const stats = ref<UserStats | null>(null)
const roles = ref<RoleItem[]>([])
const filters = reactive({ keyword: '', role_id: '' as number | '', activity: '' })

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const res: any = await getUsers({
      keyword: filters.keyword,
      role_id: filters.role_id || undefined,
      activity: filters.activity,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res: any = await getUserStats()
    stats.value = res.data
  } catch {
    stats.value = null
  }
}

async function fetchRoles() {
  try {
    const res: any = await getUserRoles()
    roles.value = res.data || []
  } catch { /* 角色加载失败时仅影响筛选项与表单 */ }
}

function applyFilters() {
  resetPagination()
  fetchData({ page: 1 })
}

function filterNoRole() {
  filters.activity = 'no_role'
  applyFilters()
}

const activeRateFoot = computed(() => {
  const s = stats.value
  if (!s) return ''
  const rate = s.total_users > 0 ? Math.round((s.active_7d / s.total_users) * 100) : 0
  return `占比 ${rate}% · 活跃口径：有登录记录`
})

const roleCodeMap = computed(() => Object.fromEntries(roles.value.map((r) => [r.id, r.code])))
function roleTagClass(role: { id: number }) {
  const code = roleCodeMap.value[role.id]
  if (code === 'super_admin') return 'danger'
  if (code === 'viewer') return 'info'
  return 'primary'
}

// ─── 头像（与审计页同一调色板） ───────────────────────────
const AVATAR_PALETTE = ['#5e6ad2', '#0e9f6e', '#b7791f', '#718096', '#c2410c', '#0369a1']
function avatarColor(name: string) {
  if (!name) return AVATAR_PALETTE[0]
  let hash = 0
  for (const ch of name) hash = (hash * 31 + (ch.codePointAt(0) || 0)) >>> 0
  return AVATAR_PALETTE[hash % AVATAR_PALETTE.length]
}
function avatarChar(name: string) {
  if (!name) return '?'
  const ch = [...name][0] || '?'
  return /[a-z]/.test(ch) ? ch.toUpperCase() : ch
}

// ─── 时间格式化 ──────────────────────────────────────────
function pad(n: number) { return String(n).padStart(2, '0') }
function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}
function absoluteTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
function dateOnly(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function loginMainText(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (isSameDay(d, now)) return `今天 ${hm}`
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
  if (isSameDay(d, yesterday)) return `昨天 ${hm}`
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000)
  return `${days} 天前`
}
function createdAgoText(iso: string | null): string {
  if (!iso) return ''
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days < 1) return '今天创建'
  if (days < 30) return `${days} 天前`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} 个月前`
  return `${Math.floor(months / 12)} 年前`
}
function relativeShort(iso: string | null): string {
  if (!iso) return '-'
  return loginMainText(iso)
}

// ─── 新建 / 编辑弹窗 ──────────────────────────────────────
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({ username: '', full_name: '', password: '', role_ids: [] as number[] })

function toggleRole(id: number) {
  const i = form.role_ids.indexOf(id)
  if (i >= 0) form.role_ids.splice(i, 1)
  else form.role_ids.push(id)
}

function showDialog(row?: UserItem) {
  editingId.value = row?.id || null
  Object.assign(form, row
    ? { username: row.username, full_name: row.full_name, password: '', role_ids: row.roles.map((r) => r.id) }
    : { username: '', full_name: '', password: '', role_ids: [] })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.username.trim() || !form.full_name.trim()) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  if (!editingId.value && form.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateUser(editingId.value, { username: form.username.trim(), full_name: form.full_name.trim(), role_ids: form.role_ids })
      ElMessage.success('更新成功')
    } else {
      await createUser({ username: form.username.trim(), full_name: form.full_name.trim(), password: form.password, role_ids: form.role_ids })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await Promise.all([fetchData(), fetchStats()])
  } finally {
    saving.value = false
  }
}

// ─── 重置密码 ────────────────────────────────────────────
const resetVisible = ref(false)
const resetTarget = ref<UserItem | null>(null)
const resetting = ref(false)
const resetForm = reactive({ password: '', confirm: '' })

function showReset(row: UserItem) {
  resetTarget.value = row
  resetForm.password = ''
  resetForm.confirm = ''
  resetVisible.value = true
}

async function handleResetSave() {
  if (resetForm.password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (resetForm.password !== resetForm.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  resetting.value = true
  try {
    await resetUserPassword(resetTarget.value!.id, resetForm.password)
    ElMessage.success(`已重置「${resetTarget.value!.username}」的密码`)
    resetVisible.value = false
  } finally {
    resetting.value = false
  }
}

// ─── 删除 ────────────────────────────────────────────────
async function handleDelete(row: UserItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除用户「${row.username}」（${row.full_name}）？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await deleteUser(row.id)
  ElMessage.success('删除成功')
  await Promise.all([fetchData(), fetchStats()])
}

// ─── 用户详情抽屉 ─────────────────────────────────────────
const detailVisible = ref(false)
const detailUser = ref<UserItem | null>(null)
const detailActivity = ref<UserActivity | null>(null)
const detailLoading = ref(false)

async function showDetail(row: UserItem) {
  detailUser.value = row
  detailActivity.value = null
  detailVisible.value = true
  detailLoading.value = true
  try {
    const res: any = await getUserActivity(row.id)
    detailActivity.value = res.data
  } finally {
    detailLoading.value = false
  }
}

const ACTION_LABELS: Record<string, string> = {
  login: '登录成功',
  login_failed: '登录失败',
  logout: '登出',
  create: '新增',
  update: '编辑',
  delete: '删除',
}
function actionLabel(action: string) {
  return ACTION_LABELS[action] || action
}
function tlDotClass(action: string) {
  if (action === 'login') return 'ok'
  if (action === 'login_failed') return 'bad'
  return 'info'
}

onMounted(() => {
  fetchData()
  fetchStats()
  fetchRoles()
})
</script>

<style scoped>
.page-subtitle {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}

/* ═══ 统计卡 ═══ */
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.stat {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.stat.clickable {
  cursor: pointer;
}
.stat.clickable:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(94, 106, 210, 0.1);
}
.stat .lbl {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}
.stat .num {
  margin-top: 3px;
  font-size: 17px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.stat .num.warn {
  color: var(--warning-color);
}
.stat .foot {
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--text-muted);
}
.stat .foot .bad {
  color: var(--danger-color);
  font-weight: 600;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}
.dot-p { background: var(--primary-color); }
.dot-s { background: var(--success-color); }
.dot-w { background: var(--warning-color); }
.dot-d { background: var(--danger-color); }

/* ═══ 卡片 + 工具栏 ═══ */
.table-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}
.search-input {
  width: 220px;
}
.filter-select {
  width: 150px;
}
.spacer {
  flex: 1;
}
.meta {
  font-size: 12px;
  color: var(--text-muted);
}

/* ═══ 表格 ═══ */
.user-table {
  --el-table-row-hover-bg-color: var(--primary-bg);
}
.user-table :deep(.el-table__header th) {
  background: #f7f7f9;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}
.user-table :deep(.el-table__row) {
  cursor: pointer;
}
.u-cell {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}
.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex: none;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
}
.avatar.lg {
  width: 40px;
  height: 40px;
  font-size: 16px;
}
.u-name {
  min-width: 0;
}
.u-name strong {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 650;
  color: var(--text-primary);
}
.u-name span {
  display: block;
  font-size: 11.5px;
  color: var(--text-muted);
}
.me-badge {
  font-size: 10px;
  font-weight: 700;
  color: var(--primary-color);
  background: var(--primary-bg);
  border-radius: 4px;
  padding: 0 5px;
  line-height: 16px;
}
.role-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 999px;
  white-space: nowrap;
}
.tag::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.tag.ok { color: #16a34a; background: rgba(34, 197, 94, 0.11); }
.tag.primary { color: var(--primary-color); background: var(--primary-bg); }
.tag.warn { color: #d97706; background: rgba(245, 158, 11, 0.13); }
.tag.danger { color: #dc2626; background: rgba(239, 68, 68, 0.09); }
.tag.info { color: var(--text-secondary); background: rgba(140, 140, 140, 0.12); }
.time-cell {
  white-space: nowrap;
  color: var(--text-primary);
}
.time-cell span {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}
.time-cell .never {
  color: var(--text-muted);
  font-size: 12.5px;
}

/* 操作列 */
.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.action-cell :deep(.el-button + .el-button) {
  margin-left: 0;
}
.action-cell :deep(.el-dropdown) {
  margin-left: 0;
}
.action-more {
  color: var(--text-secondary);
}
.action-more-icon {
  margin-left: 2px;
  font-size: 12px;
}
.text-danger {
  color: #dc2626;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 11px 12px;
}

/* ═══ 弹窗 ═══ */
.dlg-body {
  padding: 2px 0;
}
.fld {
  margin-bottom: 14px;
}
.fld:last-child {
  margin-bottom: 0;
}
.fld-k {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.fld-k em {
  color: var(--danger-color);
  font-style: normal;
}
.hint {
  margin-top: 5px;
  font-size: 11.5px;
  color: var(--text-muted);
}
.reset-tip {
  margin: 0 0 14px;
  font-size: 12.5px;
  color: var(--text-secondary);
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 7px;
  padding: 8px 10px;
}
.role-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.role-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 9px 10px;
  cursor: pointer;
  transition: all 0.12s;
  position: relative;
}
.role-card:hover {
  border-color: var(--primary-color);
}
.role-card.on {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}
.role-card.on::after {
  content: '✓';
  position: absolute;
  top: 7px;
  right: 9px;
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
}
.role-card strong {
  display: block;
  font-size: 12.5px;
  color: var(--text-primary);
}
.role-card span {
  font-size: 11px;
  color: var(--text-muted);
}

/* ═══ 用户详情抽屉 ═══ */
:deep(.el-drawer__body) {
  padding: 0;
  overflow-y: auto;
}
.d-head {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(180deg, #fbfbfc 0%, var(--surface-color) 100%);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.d-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.d-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.d-sub {
  margin-top: 3px;
  font-size: 12px;
  color: var(--text-muted);
}
.d-close {
  border: 0;
  cursor: pointer;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: var(--bg-color);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1;
  flex: none;
  transition: all 0.15s;
}
.d-close:hover {
  background: rgba(239, 68, 68, 0.09);
  color: #dc2626;
}
.d-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-bottom: 1px solid var(--border-color);
}
.d-summary > div {
  padding: 10px 14px;
  border-right: 1px solid var(--border-color);
}
.d-summary > div:last-child {
  border-right: none;
}
.d-summary .k {
  font-size: 11px;
  color: var(--text-muted);
}
.d-summary .v {
  margin-top: 2px;
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.d-summary .v.v-danger {
  color: var(--danger-color);
}
.d-sec-k {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.4px;
  padding: 14px 20px 0;
}
.timeline {
  padding: 12px 20px 20px;
}
.tl-item {
  position: relative;
  padding: 0 0 14px 22px;
}
.tl-item::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: -2px;
  width: 1px;
  background: var(--border-color);
}
.tl-item:last-child::before {
  display: none;
}
.tl-dot {
  position: absolute;
  left: 0;
  top: 4px;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid var(--surface-color);
  box-shadow: 0 0 0 1px var(--border-color);
  background: var(--text-muted);
}
.tl-dot.ok {
  background: #16a34a;
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.4);
}
.tl-dot.bad {
  background: #dc2626;
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.4);
}
.tl-dot.info {
  background: var(--primary-color);
  box-shadow: 0 0 0 1px rgba(94, 106, 210, 0.4);
}
.tl-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.tl-act {
  font-size: 12.5px;
  font-weight: 650;
  color: var(--text-primary);
}
.tl-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: auto;
}
.tl-detail {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  word-break: break-all;
}

@media (max-width: 900px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .search-input,
  .filter-select {
    width: 100%;
  }
  .role-grid {
    grid-template-columns: 1fr;
  }
}
</style>
