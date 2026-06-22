<template>
  <div class="asset-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">主机管理</h1>
        <p class="page-subtitle">
          按信息完整度和连接就绪度管理主机，优先暴露 SSH 未配置、负责人缺失和状态异常资产。
        </p>
      </div>
      <div class="heading-actions">
        <el-button :icon="Upload">批量导入</el-button>
        <el-button type="primary" :icon="Plus" @click="showDialog()">新增主机</el-button>
      </div>
    </div>

    <div class="summary-grid" role="region" aria-label="主机资产总览">
      <div class="metric-card">
        <div class="metric-label">主机总数 <span class="status-dot dot-info" /></div>
        <div class="metric-value">{{ stats.total }}</div>
        <div class="metric-foot">资产库当前记录</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">使用中 <span class="status-dot dot-success" /></div>
        <div class="metric-value is-success">{{ stats.active }}</div>
        <div class="metric-foot">{{ activeRate }} 可纳入日常操作</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">已关机 <span class="status-dot dot-warning" /></div>
        <div class="metric-value is-warning">{{ stats.shutdown }}</div>
        <div class="metric-foot">建议确认是否闲置</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">SSH 已配置 <span class="status-dot dot-success" /></div>
        <div class="metric-value">{{ inventoryStats.sshReady }}</div>
        <div class="metric-foot">密码或密钥认证</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">信息不完整 <span class="status-dot dot-danger" /></div>
        <div class="metric-value is-danger">{{ inventoryStats.incomplete }}</div>
        <div class="metric-foot">缺负责人、规格或 SSH</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">需关注 <span class="status-dot dot-danger" /></div>
        <div class="metric-value is-danger">{{ inventoryStats.attention }}</div>
        <div class="metric-foot">风险优先排在前面</div>
      </div>
    </div>

    <div class="filter-panel" role="search" aria-label="主机筛选">
      <div class="filter-left">
        <el-input
          v-model="filters.keyword"
          class="search-input"
          clearable
          :prefix-icon="Search"
          placeholder="搜索主机名、IP、负责人"
          aria-label="搜索主机名、IP、负责人"
          @keyup.enter="fetchData"
          @clear="fetchData"
        />
        <el-select v-model="filters.status" placeholder="全部状态" clearable aria-label="状态筛选" @change="fetchData">
          <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.asset_type" placeholder="全部类型" clearable aria-label="类型筛选" @change="fetchData">
          <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="sshFilter" placeholder="SSH 全部" aria-label="SSH 筛选">
          <el-option label="SSH 全部" value="" />
          <el-option label="已配置" value="ready" />
          <el-option label="未配置" value="missing" />
          <el-option label="密钥认证" value="key" />
        </el-select>
        <el-select v-model="sortMode" placeholder="排序" aria-label="排序方式">
          <el-option label="风险优先" value="risk" />
          <el-option label="最近创建" value="created" />
          <el-option label="主机名" value="name" />
          <el-option label="完整度" value="completeness" />
        </el-select>
      </div>
      <div class="filter-right">
        <el-button text @click="resetFilters">重置</el-button>
        <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
      </div>
    </div>

    <div class="asset-table-card">
      <div class="table-meta">
        <span>已筛选出 {{ filteredItems.length }} 台主机，默认将 SSH 未配置、信息缺失和异常状态排在前面。</span>
        <span>当前页 {{ items.length }} 条 / 共 {{ total }} 条</span>
      </div>
      <div class="table-wrapper">
        <el-table :data="displayItems" v-loading="loading" class="asset-table">
          <el-table-column label="主机" min-width="230">
            <template #default="{ row }">
              <div class="host-cell">
                <span class="risk-rail" :class="riskRailClass(row)" />
                <div class="cell-stack">
                  <span class="cell-primary">{{ row.name }}</span>
                  <span class="cell-secondary mono">{{ row.ip_address }} · {{ row.description || '暂无描述' }}</span>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small" round>
                <span class="tag-dot" :class="statusDotClass(row.status)" />{{ row.status }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="类型 / 系统" min-width="150">
            <template #default="{ row }">
              <div class="cell-stack">
                <span class="cell-primary">{{ row.asset_type || '-' }}</span>
                <span class="cell-secondary">{{ row.os || '系统未填写' }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="规格" min-width="130">
            <template #default="{ row }">
              <div class="cell-stack">
                <span class="cell-primary" :class="{ 'is-warning': !row.spec }">{{ row.spec || '未填写' }}</span>
                <span class="cell-secondary">硬件配置</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="负责人" min-width="130">
            <template #default="{ row }">
              <div class="cell-stack">
                <span class="cell-primary" :class="{ 'is-warning': !row.owner }">{{ row.owner || '未分配' }}</span>
                <span class="cell-secondary">责任归属</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="SSH 状态" min-width="130">
            <template #default="{ row }">
              <el-tag :type="sshTagType(row)" size="small" round>
                <span class="tag-dot" :class="sshDotClass(row)" />{{ getAssetSshState(row).label }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="完整度" min-width="150">
            <template #default="{ row }">
              <div class="completeness">
                <span class="progress-track">
                  <span class="progress-bar" :class="completenessClass(row)" :style="{ width: `${getAssetCompleteness(row).percent}%` }" />
                </span>
                <span :class="completenessTextClass(row)">{{ getAssetCompleteness(row).percent }}%</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="创建时间" min-width="120">
            <template #default="{ row }">
              <div class="cell-stack">
                <span class="cell-primary">{{ formatAssetDate(row.created_at) }}</span>
                <span class="cell-secondary">资产入库</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="190" fixed="right" align="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button size="small" type="primary" link :disabled="getAssetSshState(row).state === 'missing'" :aria-label="`SSH 连接 ${row.name}`" @click="$router.push(`/monitoring/hosts/${row.id}/ssh`)">
                  SSH
                </el-button>
                <el-button size="small" type="info" link :aria-label="`查看 ${row.name} 详情`" @click="$router.push(`/assets/${row.id}`)">详情</el-button>
                <el-popconfirm title="确认删除该资产？" @confirm="handleDelete(row.id)">
                  <template #reference>
                    <el-button size="small" type="danger" link :aria-label="`删除 ${row.name}`">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-wrap">
        <span class="pagination-total">共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          :layout="paginationLayout"
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新增主机" width="min(620px, 90vw)" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="86px" label-position="left">
        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">1</span> 基础信息</div>
          <div class="form-row">
            <el-form-item label="名称" prop="name"><el-input v-model="form.name" placeholder="如 Web-Server-01" /></el-form-item>
            <el-form-item label="类型" prop="asset_type">
              <el-select v-model="form.asset_type" class="form-control">
                <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" placeholder="如 192.168.1.100" /></el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" class="form-control">
                <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">2</span> 规格与系统</div>
          <div class="form-row">
            <el-form-item label="规格"><el-input v-model="form.spec" placeholder="如 4C8G" /></el-form-item>
            <el-form-item label="系统"><el-input v-model="form.os" placeholder="如 Ubuntu 22.04" /></el-form-item>
          </div>
          <el-form-item label="负责人"><el-input v-model="form.owner" placeholder="输入负责人姓名" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="用途说明" /></el-form-item>
        </div>

        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">3</span> SSH 连接配置</div>
          <div class="form-row">
            <el-form-item label="端口"><el-input-number v-model="form.ssh_port" :min="1" :max="65535" class="form-control" /></el-form-item>
            <el-form-item label="用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="认证方式">
              <el-select v-model="form.auth_method" class="form-control">
                <el-option label="密码" value="password" />
                <el-option label="SSH 密钥" value="key" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="form.auth_method === 'password'" label="密码">
              <el-input v-model="form.ssh_password" type="password" show-password placeholder="SSH 密码" />
            </el-form-item>
            <el-form-item v-else label="SSH 密钥">
              <el-select v-model="form.ssh_key_id" placeholder="请选择 SSH 密钥" class="form-control" clearable>
                <el-option v-for="key in sshKeys" :key="key.id" :label="`${key.name} (${key.username})`" :value="key.id">
                  <div class="key-option">
                    <span>{{ key.name }}</span>
                    <el-tag size="small" :type="key.auth_type === 'key' ? 'success' : 'info'">
                      {{ key.auth_type === 'key' ? '私钥' : '密码' }}
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { createAsset, deleteAsset, getAssets, getAssetStats } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import { usePagination } from '@/hooks/usePagination'
import {
  formatAssetDate,
  getAssetCompleteness,
  getAssetSshState,
  getCompletenessTone,
  isAttentionAsset,
  sortAssetsByRisk,
  type AssetLike,
} from '@/utils/assetDisplay'

type AssetItem = AssetLike & {
  id: number
  name: string
  asset_type: string
  ip_address: string
  status: string
}

const loading = ref(false)
const saving = ref(false)
const items = ref<AssetItem[]>([])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const sshKeys = ref<any[]>([])
const sshFilter = ref('')
const sortMode = ref('risk')

const stats = reactive({ total: 0, active: 0, shutdown: 0, deleted: 0 })

const assetTypes = ['云主机', '数据库', '网络设备', '中间件', '其他']
const statusList = [
  { label: '使用中', value: '使用中' },
  { label: '已关机', value: '已关机' },
  { label: '已删除', value: '已删除' },
]

function statusTagType(status: string) {
  const map: Record<string, 'success' | 'warning' | 'info'> = { 使用中: 'success', 已关机: 'warning', 已删除: 'info' }
  return map[status] || 'info'
}

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

const filters = reactive({ keyword: '', asset_type: '', status: '' })
const form = reactive({
  name: '',
  asset_type: '云主机',
  ip_address: '',
  status: '使用中',
  owner: '',
  description: '',
  spec: '',
  os: '',
  ssh_port: 22,
  ssh_username: 'root',
  ssh_password: '',
  auth_method: 'password' as 'password' | 'key',
  ssh_key_id: null as number | null,
})
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip_address: [{ required: true, message: '请输入 IP', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const activeRate = computed(() => {
  if (!stats.total) return '0%'
  return `${Math.round((stats.active / stats.total) * 100)}%`
})

const filteredItems = computed(() => items.value.filter((item) => {
  const ssh = getAssetSshState(item).state
  if (sshFilter.value === 'ready') return ssh === 'key' || ssh === 'password'
  if (sshFilter.value === 'missing') return ssh === 'missing' || ssh === 'partial'
  if (sshFilter.value === 'key') return ssh === 'key'
  return true
}))

const displayItems = computed(() => {
  const list = [...filteredItems.value]
  if (sortMode.value === 'created') return list.sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
  if (sortMode.value === 'name') return list.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
  if (sortMode.value === 'completeness') return list.sort((a, b) => getAssetCompleteness(a).percent - getAssetCompleteness(b).percent)
  return sortAssetsByRisk(list)
})

const inventoryStats = computed(() => {
  const base = items.value
  return {
    sshReady: base.filter((item) => ['key', 'password'].includes(getAssetSshState(item).state)).length,
    incomplete: base.filter((item) => getAssetCompleteness(item).percent < 90).length,
    attention: base.filter(isAttentionAsset).length,
  }
})

function riskRailClass(row: AssetItem) {
  const tone = getCompletenessTone(getAssetCompleteness(row).percent)
  if (getAssetSshState(row).state === 'missing') return 'danger'
  if (row.status === '已关机') return 'warning'
  return tone
}

function statusDotClass(status: string) {
  return status === '使用中' ? 'dot-success' : status === '已关机' ? 'dot-warning' : 'dot-muted'
}

function sshTagType(row: AssetItem) {
  const tone = getAssetSshState(row).tone
  return tone === 'danger' ? 'danger' : tone
}

function sshDotClass(row: AssetItem) {
  const tone = getAssetSshState(row).tone
  return tone === 'success' ? 'dot-success' : tone === 'warning' ? 'dot-warning' : 'dot-danger'
}

function completenessClass(row: AssetItem) {
  return getCompletenessTone(getAssetCompleteness(row).percent)
}

function completenessTextClass(row: AssetItem) {
  return `is-${getCompletenessTone(getAssetCompleteness(row).percent)}`
}

async function fetchStats() {
  try {
    const res: any = await getAssetStats()
    Object.assign(stats, res.data)
  } catch { /* ignore */ }
}

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getAssets(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { keyword: '', asset_type: '', status: '' })
  sshFilter.value = ''
  sortMode.value = 'risk'
  resetPagination()
  fetchData()
}

async function fetchSSHKeys() {
  try {
    const res: any = await getSSHKeys({ page_size: 100 })
    sshKeys.value = res.data?.items || []
  } catch { /* ignore */ }
}

function showDialog() {
  Object.assign(form, {
    name: '',
    asset_type: '云主机',
    ip_address: '',
    status: '使用中',
    owner: '',
    description: '',
    spec: '',
    os: '',
    ssh_port: 22,
    ssh_username: 'root',
    ssh_password: '',
    auth_method: 'password',
    ssh_key_id: null,
  })
  fetchSSHKeys()
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload: any = { ...form }
    if (payload.auth_method === 'password') {
      payload.ssh_key_id = null
    } else {
      payload.ssh_password = ''
    }
    delete payload.auth_method
    await createAsset(payload)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchData()
    fetchStats()
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  await deleteAsset(id)
  ElMessage.success('删除成功')
  fetchData()
  fetchStats()
}

onMounted(() => {
  fetchStats()
  fetchData()
})
</script>

<style scoped>
.asset-page {
  display: grid;
  gap: 14px;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.page-title {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
}

.page-subtitle {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.heading-actions,
.filter-left,
.filter-right,
.action-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.metric-card,
.filter-panel,
.asset-table-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.metric-card {
  padding: 12px 14px;
  min-width: 0;
}

.metric-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.metric-value {
  margin-top: 5px;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 750;
}

.metric-foot {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-dot,
.tag-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--text-muted);
}

.tag-dot {
  margin-right: 5px;
}

.dot-success { background: var(--success-color); }
.dot-warning { background: var(--warning-color); }
.dot-danger { background: var(--danger-color); }
.dot-info { background: #2563eb; }
.dot-muted { background: var(--text-muted); }

.is-success { color: var(--success-color); }
.is-warning { color: var(--warning-color); }
.is-danger { color: var(--danger-color); }

.filter-panel {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
}

.search-input {
  width: 292px;
}

.asset-table-card {
  overflow: hidden;
}

.table-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
}

.asset-table {
  width: 100%;
}

.asset-table :deep(.el-table__header th) {
  height: 38px;
  background: #f5f6fa;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.asset-table :deep(.el-table__row:hover > td.el-table__cell) {
  background: #fbfbfd;
}

.host-cell {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.risk-rail {
  width: 3px;
  height: 30px;
  border-radius: 99px;
  background: #d7dae3;
  flex: none;
}

.risk-rail.success { background: var(--success-color); }
.risk-rail.warning { background: var(--warning-color); }
.risk-rail.danger { background: var(--danger-color); }

.cell-stack {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.cell-primary {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.cell-secondary {
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.completeness {
  display: grid;
  grid-template-columns: 74px 52px;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #eef0f4;
}

.progress-bar {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--primary-color);
}

.progress-bar.success { background: var(--success-color); }
.progress-bar.warning { background: var(--warning-color); }
.progress-bar.danger { background: var(--danger-color); }

.pagination-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 11px 12px;
  border-top: 1px solid var(--border-color);
}

.pagination-total {
  color: var(--text-secondary);
  font-size: 13px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  color: var(--primary-color);
  font-size: 13px;
  font-weight: 600;
}

.form-group-number {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--primary-bg);
  font-size: 11px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.form-control {
  width: 100%;
}

.key-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .page-heading,
  .filter-panel,
  .table-meta,
  .pagination-wrap {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .search-input,
  .filter-left :deep(.el-select) {
    width: 100%;
  }

  .heading-actions,
  .filter-left,
  .filter-right {
    width: 100%;
  }
}

@media (max-width: 520px) {
  .summary-grid,
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
