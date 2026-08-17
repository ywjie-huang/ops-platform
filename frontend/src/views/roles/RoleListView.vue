<template>
  <div>
    <!-- ═══ 页头 ═══ -->
    <div class="page-header">
      <div>
        <h2 class="page-title">角色权限</h2>
        <p class="page-subtitle">角色定义、菜单授权与成员覆盖的统一管理。</p>
      </div>
      <el-button type="primary" size="small" @click="showDialog()">
        <el-icon><Plus /></el-icon>新增角色
      </el-button>
    </div>

    <!-- ═══ 统计卡 ═══ -->
    <div class="stats" role="region" aria-label="角色概览">
      <div class="stat">
        <div class="lbl"><span class="dot dot-p" aria-hidden="true"></span>角色总数</div>
        <div class="num">{{ stats?.total_roles ?? '-' }}</div>
        <div class="foot">{{ stats ? `系统内置 ${stats.system_roles} · 自定义 ${stats.custom_roles}` : '' }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-s" aria-hidden="true"></span>已分配账号</div>
        <div class="num">{{ stats?.assigned_users ?? '-' }}</div>
        <div class="foot">{{ coverageFoot }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-w" aria-hidden="true"></span>权限点</div>
        <div class="num">{{ stats?.perm_total ?? '-' }}</div>
        <div class="foot">{{ stats ? `覆盖 ${stats.perm_modules} 个功能模块` : '' }}</div>
      </div>
      <div class="stat clickable" title="点击筛选未配置权限的角色" role="button" tabindex="0" @click="filterNoPerm" @keyup.enter="filterNoPerm">
        <div class="lbl"><span class="dot dot-d" aria-hidden="true"></span>空权限角色</div>
        <div class="num" :class="{ warn: (stats?.no_perm_roles ?? 0) > 0 }">{{ stats?.no_perm_roles ?? '-' }}</div>
        <div class="foot">未配置任何权限点，点击筛选</div>
      </div>
    </div>

    <div class="table-card">
      <!-- ═══ 工具栏 ═══ -->
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索角色名称、编码、说明…"
          clearable
          class="search-input"
          :prefix-icon="Search"
          aria-label="搜索角色"
          @keyup.enter="applyFilters"
          @clear="applyFilters"
        />
        <el-select v-model="filters.type" class="filter-select" aria-label="按类型筛选" @change="applyFilters">
          <el-option value="" label="类型：全部" />
          <el-option value="system" label="系统内置" />
          <el-option value="custom" label="自定义" />
        </el-select>
        <span class="spacer"></span>
        <span class="meta">共 {{ total }} 个角色</span>
      </div>
      <!-- ═══ 角色表格 ═══ -->
      <el-table :data="items" v-loading="loading" class="role-table">
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <div class="role-name">
              {{ row.name }}
              <span class="tag sm" :class="row.is_system ? 'danger' : 'primary'">{{ row.is_system ? '内置' : '自定义' }}</span>
            </div>
            <span class="role-code">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="权限点" width="150">
          <template #default="{ row }">
            <div v-if="row.permissions?.length" class="perm-cell">
              <strong>{{ row.permissions.length }}</strong>
              <span>覆盖 {{ moduleCount(row) }} 个模块</span>
            </div>
            <div v-else class="perm-cell"><span class="tag warn">未配置</span></div>
          </template>
        </el-table-column>
        <el-table-column label="成员" width="90">
          <template #default="{ row }">
            <span class="member-cell" :class="{ zero: !row.user_count }">{{ row.user_count }} 人</span>
          </template>
        </el-table-column>
        <el-table-column label="说明" min-width="180">
          <template #default="{ row }">
            <div class="desc-cell" :title="row.description">{{ row.description || '—' }}</div>
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
        <el-table-column label="操作" width="185" align="center">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button size="small" type="primary" link :aria-label="`编辑 ${row.name}`" @click="showDialog(row)">编辑</el-button>
              <el-tooltip
                content="超级管理员默认拥有全部权限，无需配置"
                :disabled="row.code !== 'super_admin'"
                placement="top"
              >
                <span class="action-slot">
                  <el-button
                    size="small" type="primary" link
                    :disabled="row.code === 'super_admin'"
                    :aria-label="`配置 ${row.name} 的权限`"
                    @click="showPermDrawer(row)"
                  >权限配置</el-button>
                </span>
              </el-tooltip>
              <el-dropdown trigger="click" placement="bottom-end" :aria-label="`${row.name} 更多操作`" @command="() => handleDelete(row)">
                <el-button size="small" link class="action-more">
                  更多<el-icon class="action-more-icon"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="delete" :disabled="!!deleteDisabledReason(row)" :title="deleteDisabledReason(row)">
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
    <!-- ═══ 新增/编辑角色弹窗 ═══ -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑角色' : '新增角色'" width="480px" :close-on-click-modal="false" destroy-on-close>
      <div class="dlg-body">
        <div class="fld">
          <div class="fld-k"><em>*</em> 角色名称</div>
          <el-input v-model="form.name" placeholder="如：运维工程师" />
        </div>
        <div class="fld">
          <div class="fld-k"><em>*</em> 角色编码</div>
          <el-input v-model="form.code" placeholder="如：ops（字母、数字、下划线）" :disabled="!!editingId" />
          <div class="hint">编码用于权限标识，创建后不可修改；系统内置角色的编码锁定</div>
        </div>
        <div class="fld">
          <div class="fld-k">说明</div>
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="这个角色能做什么、给谁用" />
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- ═══ 权限配置抽屉 ═══ -->
    <el-drawer v-model="permVisible" size="720px" :with-header="false" destroy-on-close>
      <div class="d-head">
        <div>
          <div class="d-title">权限配置 <span class="tag primary">{{ permRole?.name }}</span></div>
          <div class="d-sub">{{ permRole?.code }} · 保存后用户刷新页面生效</div>
        </div>
        <button type="button" class="d-close" aria-label="关闭" @click="permVisible = false">✕</button>
      </div>
      <div class="perm-toolbar">
        <el-input v-model="permKeyword" placeholder="过滤权限点…" clearable class="perm-filter" aria-label="过滤权限点" />
        <div class="batch-group">
          <span class="bl">批量</span>
          <button type="button" class="chip" @click="selectAll">全选</button>
          <button type="button" class="chip" @click="clearAll">清空</button>
        </div>
        <div class="batch-group">
          <span class="bl">按操作</span>
          <button
            v-for="a in ACTION_CHIPS" :key="a.key" type="button"
            class="chip" :class="{ on: isActionOn(a.key) }"
            @click="toggleAction(a.key)"
          >{{ a.label }}</button>
        </div>
        <span class="spacer"></span>
        <span class="perm-count">已选 <strong>{{ permChecked.size }}</strong> / {{ totalPerms }}</span>
      </div>
      <div class="perm-body">
        <div v-for="group in filteredTree" :key="group.parent" class="pg-group">
          <div class="pg-head">
            <span
              class="cb lg" :class="parentCbClass(group)"
              role="checkbox" :aria-checked="parentCbClass(group) === 'on'" tabindex="0"
              @click="toggleParent(group)" @keyup.enter="toggleParent(group)"
            >{{ group.parent }}</span>
            <span class="prog">{{ groupCheckedCount(group) }} / {{ groupTotalCount(group) }}</span>
          </div>
          <div v-for="child in group.children" :key="child.module" class="pg-row">
            <div class="pg-mod">
              <span
                class="cb" :class="childCbClass(child)"
                role="checkbox" :aria-checked="childCbClass(child) === 'on'" tabindex="0"
                @click="toggleChild(child)" @keyup.enter="toggleChild(child)"
              >{{ child.label }}</span>
            </div>
            <div class="pg-perms">
              <span
                v-for="p in child.permissions" :key="p.id"
                class="cb" :class="{ on: permChecked.has(p.id) }"
                role="checkbox" :aria-checked="permChecked.has(p.id)" tabindex="0"
                @click="togglePerm(p)" @keyup.enter="togglePerm(p)"
              >{{ p.name }}</span>
            </div>
          </div>
        </div>
        <el-empty v-if="permKeyword && !filteredTree.length" description="没有匹配的权限点" :image-size="80" />
      </div>
      <div class="d-foot">
        <span class="summary">已选 <strong>{{ permChecked.size }}</strong> 项 · 覆盖 <strong>{{ coveredModules }}</strong> 个模块</span>
        <span class="gap"></span>
        <el-button @click="permVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPerm" @click="handleSavePerm">保存</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Search } from '@element-plus/icons-vue'
import {
  getRoles, getRoleStats, createRole, updateRole, deleteRole,
  assignPermissions, getPermissionTree,
  type RoleItem, type RoleStats, type PermGroup, type PermItem,
} from '@/api/roles'
import { usePagination } from '@/hooks/usePagination'

// ─── 列表 ────────────────────────────────────────────────
const loading = ref(false)
const items = ref<RoleItem[]>([])
const stats = ref<RoleStats | null>(null)
const filters = reactive({ keyword: '', type: '', no_perm: false })

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const res: any = await getRoles({
      keyword: filters.keyword,
      type: filters.type,
      no_perm: filters.no_perm || undefined,
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
    const res: any = await getRoleStats()
    stats.value = res.data
  } catch {
    stats.value = null
  }
}

function applyFilters() {
  resetPagination()
  fetchData({ page: 1 })
}

function filterNoPerm() {
  filters.no_perm = true
  applyFilters()
}

const coverageFoot = computed(() => {
  const s = stats.value
  if (!s) return ''
  const rate = s.total_users > 0 ? Math.round((s.assigned_users / s.total_users) * 100) : 0
  return `覆盖率 ${rate}%（${s.assigned_users} / ${s.total_users} 个用户）`
})

function moduleCount(row: RoleItem) {
  return new Set((row.permissions || []).map((p) => p.module)).size
}

function deleteDisabledReason(row: RoleItem) {
  if (row.is_system) return '系统内置角色不可删除'
  if (row.user_count > 0) return `仍有 ${row.user_count} 个成员，无法删除`
  return ''
}

// ─── 时间格式化 ──────────────────────────────────────────
function pad(n: number) { return String(n).padStart(2, '0') }
function dateOnly(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
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

// ─── 新增 / 编辑角色 ──────────────────────────────────────
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({ name: '', code: '', description: '' })

function showDialog(row?: RoleItem) {
  editingId.value = row?.id || null
  Object.assign(form, row
    ? { name: row.name, code: row.code, description: row.description }
    : { name: '', code: '', description: '' })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写角色名称')
    return
  }
  if (!editingId.value) {
    if (!form.code.trim()) {
      ElMessage.warning('请填写角色编码')
      return
    }
    if (!/^[a-zA-Z0-9_]+$/.test(form.code.trim())) {
      ElMessage.warning('编码仅支持字母、数字、下划线')
      return
    }
  }
  saving.value = true
  try {
    const payload = { name: form.name.trim(), code: form.code.trim(), description: form.description.trim() }
    if (editingId.value) {
      await updateRole(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createRole(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await Promise.all([fetchData(), fetchStats()])
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: RoleItem) {
  if (deleteDisabledReason(row)) return
  try {
    await ElMessageBox.confirm(
      `确认删除角色「${row.name}」？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await deleteRole(row.id)
  ElMessage.success('删除成功')
  await Promise.all([fetchData(), fetchStats()])
}

// ─── 权限配置抽屉 ─────────────────────────────────────────
const permVisible = ref(false)
const permRole = ref<RoleItem | null>(null)
const savingPerm = ref(false)
const permKeyword = ref('')
const permTree = ref<PermGroup[]>([])
const permChecked = ref(new Set<number>())

const ACTION_CHIPS = [
  { key: 'view', label: '查看' },
  { key: 'create', label: '新增' },
  { key: 'update', label: '修改' },
  { key: 'delete', label: '删除' },
]

const allPerms = computed<PermItem[]>(() =>
  permTree.value.flatMap((g) => g.children.flatMap((c) => c.permissions)),
)
const totalPerms = computed(() => allPerms.value.length)
const coveredModules = computed(() =>
  new Set(allPerms.value.filter((p) => permChecked.value.has(p.id)).map((p) => p.module)).size,
)

const filteredTree = computed<PermGroup[]>(() => {
  const kw = permKeyword.value.trim().toLowerCase()
  if (!kw) return permTree.value
  return permTree.value
    .map((g) => {
      if (g.parent.toLowerCase().includes(kw)) return g
      const children = g.children
        .map((c) => {
          if (c.label.toLowerCase().includes(kw)) return c
          return { ...c, permissions: c.permissions.filter((p) => p.name.toLowerCase().includes(kw) || p.code.toLowerCase().includes(kw)) }
        })
        .filter((c) => c.permissions.length)
      return { ...g, children }
    })
    .filter((g) => g.children.length)
})

async function showPermDrawer(row: RoleItem) {
  permRole.value = row
  permKeyword.value = ''
  permChecked.value = new Set((row.permissions || []).map((p) => p.id))
  if (!permTree.value.length) {
    const res: any = await getPermissionTree()
    permTree.value = res.data || []
  }
  permVisible.value = true
}

function parentIds(group: PermGroup) {
  return group.children.flatMap((c) => c.permissions.map((p) => p.id))
}
function parentCbClass(group: PermGroup) {
  const ids = parentIds(group)
  const n = ids.filter((id) => permChecked.value.has(id)).length
  if (n === 0) return ''
  return n === ids.length ? 'on' : 'half'
}
function toggleParent(group: PermGroup) {
  const on = parentCbClass(group) === 'on'
  parentIds(group).forEach((id) => (on ? permChecked.value.delete(id) : permChecked.value.add(id)))
}
function childCbClass(child: { permissions: PermItem[] }) {
  const n = child.permissions.filter((p) => permChecked.value.has(p.id)).length
  if (n === 0) return ''
  return n === child.permissions.length ? 'on' : 'half'
}
function toggleChild(child: { permissions: PermItem[] }) {
  const on = childCbClass(child) === 'on'
  child.permissions.forEach((p) => (on ? permChecked.value.delete(p.id) : permChecked.value.add(p.id)))
}
function togglePerm(p: PermItem) {
  if (permChecked.value.has(p.id)) permChecked.value.delete(p.id)
  else permChecked.value.add(p.id)
}
function groupCheckedCount(group: PermGroup) {
  return parentIds(group).filter((id) => permChecked.value.has(id)).length
}
function groupTotalCount(group: PermGroup) {
  return parentIds(group).length
}

function permsOfAction(action: string) {
  return allPerms.value.filter((p) => p.code.split('.')[1] === action)
}
function isActionOn(action: string) {
  const ps = permsOfAction(action)
  return ps.length > 0 && ps.every((p) => permChecked.value.has(p.id))
}
function toggleAction(action: string) {
  const on = isActionOn(action)
  permsOfAction(action).forEach((p) => (on ? permChecked.value.delete(p.id) : permChecked.value.add(p.id)))
}
function selectAll() {
  allPerms.value.forEach((p) => permChecked.value.add(p.id))
}
function clearAll() {
  permChecked.value.clear()
}

async function handleSavePerm() {
  if (!permRole.value) return
  savingPerm.value = true
  try {
    await assignPermissions(permRole.value.id, Array.from(permChecked.value))
    ElMessage.success(`已保存「${permRole.value.name}」的权限配置`)
    permVisible.value = false
    await Promise.all([fetchData(), fetchStats()])
  } finally {
    savingPerm.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchStats()
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
  width: 130px;
}
.spacer {
  flex: 1;
}
.meta {
  font-size: 12px;
  color: var(--text-muted);
}

/* ═══ 表格 ═══ */
.role-table {
  --el-table-row-hover-bg-color: var(--primary-bg);
}
.role-table :deep(.el-table__header th) {
  background: #f7f7f9;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}
.role-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 650;
  color: var(--text-primary);
}
.role-code {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  margin-top: 1px;
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
.tag.sm {
  font-size: 10.5px;
  padding: 0 7px;
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
.perm-cell strong {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.perm-cell span {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}
.perm-cell .tag {
  display: inline-flex;
}
.member-cell {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.member-cell.zero {
  color: var(--text-muted);
}
.desc-cell {
  color: var(--text-secondary);
  font-size: 12px;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
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
.action-slot {
  display: inline-flex;
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

/* ═══ 角色弹窗 ═══ */
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

/* ═══ 权限配置抽屉 ═══ */
:deep(.el-drawer__body) {
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
:deep(.el-drawer__body) .perm-body {
  flex: 1;
}
.d-head {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(180deg, #fbfbfc 0%, var(--surface-color) 100%);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.d-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
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
.perm-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}
.perm-filter {
  width: 200px;
}
.batch-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
.batch-group .bl {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-right: 2px;
}
.chip {
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11.5px;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-secondary);
  transition: all 0.12s;
}
.chip:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.chip.on {
  border-color: var(--primary-color);
  background: var(--primary-bg);
  color: var(--primary-color);
  font-weight: 600;
}
.perm-count {
  font-size: 12px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.perm-count strong {
  color: var(--primary-color);
  font-weight: 700;
}
.perm-body {
  padding: 12px 20px 16px;
}
.pg-group {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 10px;
}
.pg-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  background: #f7f7f9;
  border-bottom: 1px solid var(--border-color);
}
.pg-head .prog {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.pg-row {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}
.pg-row:last-child {
  border-bottom: none;
}
.pg-mod {
  width: 130px;
  flex: none;
  padding: 8px 12px;
  border-right: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
}
.pg-perms {
  flex: 1;
  padding: 7px 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  align-items: center;
}

/* 自定义复选框（与设计稿一致的方形样式） */
.cb {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  user-select: none;
}
.cb::before {
  content: '';
  width: 13px;
  height: 13px;
  border-radius: 4px;
  flex: none;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  transition: all 0.12s;
}
.cb:hover::before {
  border-color: var(--primary-color);
}
.cb.on {
  color: var(--text-primary);
}
.cb.on::before {
  background: var(--primary-color);
  border-color: var(--primary-color);
  box-shadow: inset 0 0 0 2px #fff;
}
.cb.half::before {
  background: linear-gradient(135deg, var(--primary-color) 50%, var(--surface-color) 50%);
  border-color: var(--primary-color);
}
.cb.lg {
  font-weight: 600;
  color: var(--text-primary);
}
.d-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  background: #f7f7f9;
}
.d-foot .summary {
  font-size: 12px;
  color: var(--text-secondary);
}
.d-foot .summary strong {
  color: var(--primary-color);
}
.d-foot .gap {
  flex: 1;
}

@media (max-width: 900px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .search-input,
  .filter-select,
  .perm-filter {
    width: 100%;
  }
  .pg-mod {
    width: 100px;
  }
}
</style>
