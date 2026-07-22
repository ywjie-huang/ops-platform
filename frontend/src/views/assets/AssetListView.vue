<template>
  <div class="asset-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">主机管理</h1>
        <p class="page-subtitle">管理主机资产台账与 SSH 接入，点击统计卡可快速定位待处理主机。</p>
      </div>
      <div class="heading-actions">
        <el-button :icon="Upload">批量导入</el-button>
        <el-button :icon="Download" :loading="exporting" @click="exportAll">导出</el-button>
        <el-button type="primary" :icon="Plus" @click="showDialog()">新增主机</el-button>
      </div>
    </div>

    <div class="summary-grid" role="region" aria-label="主机资产总览">
      <div
        v-for="card in cards"
        :key="card.key"
        class="metric-card"
        :class="{ active: activeCard === card.key }"
        role="button"
        tabindex="0"
        @click="toggleCard(card.key)"
        @keyup.enter="toggleCard(card.key)"
      >
        <div class="metric-label">{{ card.label }} <span class="status-dot" :class="card.dot" /></div>
        <div class="metric-value" :class="card.valueClass">
          {{ card.value }}<span v-if="card.ratio" class="metric-ratio">{{ card.ratio }}</span>
        </div>
        <div class="metric-foot">{{ card.foot }}</div>
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
        />
        <el-select v-model="filters.status" placeholder="全部状态" clearable aria-label="状态筛选" @change="applyFilters">
          <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.asset_type" placeholder="全部类型" clearable aria-label="类型筛选" @change="applyFilters">
          <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="sshFilter" placeholder="SSH 全部" aria-label="SSH 筛选" @change="applyFilters">
          <el-option label="SSH 全部" value="" />
          <el-option label="已配置" value="ready" />
          <el-option label="未配置" value="missing" />
          <el-option label="密钥认证" value="key" />
        </el-select>
      </div>
      <div class="filter-right">
        <el-button text @click="resetFilters">重置</el-button>
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <div v-if="selectedRows.length" class="batch-bar">
      <span class="batch-bar-count">已选 <b>{{ selectedRows.length }}</b> 台主机</span>
      <el-button link type="primary" @click="openOwnerDialog">批量分配负责人</el-button>
      <el-button link type="primary" @click="exportSelected">导出所选</el-button>
      <el-button link type="danger" :loading="batchLoading" @click="handleBatchDelete">批量删除</el-button>
      <span class="batch-bar-spacer" />
      <el-button link @click="clearSelection">取消选择</el-button>
    </div>

    <div class="asset-table-card">
      <div class="table-meta">
        <span>共 {{ total }} 台主机，默认按风险优先排序（SSH 未配置、信息缺失和异常状态排在前面）。</span>
        <span>当前页 {{ items.length }} 条</span>
      </div>
      <div class="table-wrapper">
        <el-table
          ref="tableRef"
          :data="items"
          v-loading="loading"
          class="asset-table"
          @selection-change="handleSelectionChange"
          @sort-change="handleSortChange"
        >
          <el-table-column type="selection" width="40" />
          <el-table-column label="主机" min-width="230" prop="name" sortable="custom">
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

          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small" round>
                <span class="tag-dot" :class="statusDotClass(row.status)" />{{ row.status }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="类型 / 规格" min-width="170">
            <template #default="{ row }">
              <div class="cell-stack">
                <span class="cell-primary">{{ row.asset_type || '-' }}</span>
                <span class="cell-secondary">
                  <template v-if="row.spec">{{ row.spec }}</template>
                  <span v-else class="is-warning">规格未填写</span>
                  · {{ row.os || '系统未填写' }}
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="负责人" min-width="110" prop="owner" sortable="custom">
            <template #default="{ row }">
              <span class="cell-primary" :class="{ 'is-warning': !row.owner }">{{ row.owner || '未分配' }}</span>
            </template>
          </el-table-column>

          <el-table-column label="SSH" min-width="110">
            <template #default="{ row }">
              <el-tag :type="sshTagType(row)" size="small" round>
                <span class="tag-dot" :class="sshDotClass(row)" />{{ getAssetSshState(row).label }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="完整度" min-width="150" prop="completeness" sortable="custom">
            <template #default="{ row }">
              <el-tooltip :content="completenessTip(row)" placement="top" :show-after="200">
                <div class="completeness">
                  <span class="progress-track">
                    <span class="progress-bar" :class="completenessClass(row)" :style="{ width: `${getAssetCompleteness(row).percent}%` }" />
                  </span>
                  <span :class="completenessTextClass(row)">{{ getAssetCompleteness(row).percent }}%</span>
                </div>
              </el-tooltip>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="170" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button size="small" type="primary" link :aria-label="`查看 ${row.name} 详情`" @click="$router.push(`/assets/hosts/${row.public_id}`)">详情</el-button>
                <el-button size="small" type="primary" link :aria-label="`编辑 ${row.name}`" @click="showDialog(row)">编辑</el-button>
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

    <el-drawer
      v-model="dialogVisible"
      :title="editingRow ? `编辑主机 · ${editingRow.name}` : '新增主机'"
      direction="rtl"
      size="560px"
      destroy-on-close
      class="asset-drawer"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">1</span> 基础信息</div>
          <div class="form-row">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" placeholder="如 Web-Server-01" />
            </el-form-item>
            <el-form-item label="类型" prop="asset_type">
              <el-select v-model="form.asset_type" class="form-control">
                <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="IP 地址" prop="ip_address">
              <el-input v-model="form.ip_address" placeholder="如 192.168.1.100" />
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" class="form-control">
                <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
          </div>
        </div>


        <el-divider class="form-divider" />

        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">2</span> 规格与系统</div>
          <div class="form-row">
            <el-form-item label="规格">
              <el-input v-model="form.spec" placeholder="如 4C8G" />
            </el-form-item>
            <el-form-item label="操作系统">
              <el-input v-model="form.os" placeholder="如 Ubuntu 22.04" />
            </el-form-item>
          </div>
          <el-form-item label="负责人">
            <el-autocomplete
              v-model="form.owner"
              :fetch-suggestions="fetchOwnerSuggestions"
              placeholder="输入姓名搜索，或直接填写"
              clearable
              class="form-control"
            />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="用途说明" />
          </el-form-item>
        </div>


        <el-divider class="form-divider" />

        <div class="form-group form-group--last">
          <div class="form-group-title">
            <span class="form-group-number">3</span> SSH 连接配置
            <span class="form-group-hint">可选，稍后在详情页配置</span>
          </div>
          <div class="form-row">
            <el-form-item label="端口" prop="ssh_port">
              <el-input-number v-model="form.ssh_port" :min="1" :max="65535" controls-position="right" class="form-control" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="form.ssh_username" placeholder="root" />
            </el-form-item>
          </div>
          <el-form-item label="认证方式">
            <el-radio-group v-model="form.auth_method" class="auth-method-group">
              <el-radio-button value="password">密码</el-radio-button>
              <el-radio-button value="key">SSH 密钥</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-show="form.auth_method === 'password'" :label="editingRow ? '密码（留空则不修改）' : '密码'" class="credential-form-item">
            <el-input v-model="form.ssh_password" type="password" show-password :placeholder="editingRow ? '留空则保持原密码' : 'SSH 登录密码'" />
          </el-form-item>
          <el-form-item v-show="form.auth_method === 'key'" label="SSH 密钥" class="credential-form-item">
            <el-select v-model="form.ssh_key_id" placeholder="请选择 SSH 密钥" class="form-control" clearable>
              <template #empty>
                <div class="key-empty">
                  暂无密钥，<el-link type="primary" @click="goToSSHKeys">去创建</el-link>
                </div>
              </template>
              <el-option
                v-for="key in sshKeys"
                :key="key.id"
                :label="`${key.name} (${key.username})`"
                :value="key.id"
              >
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
      </el-form>

      <template #footer>
        <div class="drawer-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <div class="drawer-footer-right">
            <el-button v-if="!editingRow" :loading="saving" @click="handleSave(true)">保存并继续</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave(false)">保存</el-button>
          </div>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="ownerDialogVisible" title="批量分配负责人" width="420px" destroy-on-close>
      <p class="owner-dialog-tip">将为选中的 {{ selectedRows.length }} 台主机统一设置负责人：</p>
      <el-autocomplete
        v-model="ownerInput"
        :fetch-suggestions="fetchOwnerSuggestions"
        placeholder="输入姓名搜索，或直接填写"
        clearable
        class="form-control"
        @keyup.enter="submitBatchOwner"
      />
      <template #footer>
        <el-button @click="ownerDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchLoading" @click="submitBatchOwner">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type TableInstance } from 'element-plus'
import { Download, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { createAsset, deleteAsset, getAssets, getAssetStats, updateAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import { getUsers } from '@/api/users'
import { usePagination } from '@/hooks/usePagination'
import {
  buildAssetPayload,
  createAssetForm,
  createAssetFormFromAsset,
  isValidIpAddress,
  type AssetForm,
} from '@/utils/assetForm'
import {
  formatAssetDate,
  getAssetCompleteness,
  getAssetMissingFields,
  getAssetSshState,
  getCompletenessTone,
  type AssetLike,
} from '@/utils/assetDisplay'

type AssetItem = AssetLike & {
  id: number
  public_id: string
  name: string
  asset_type: string
  ip_address: string
  status: string
}

type CardKey = 'all' | 'active' | 'sshReady' | 'sshMissing'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const batchLoading = ref(false)
const items = ref<AssetItem[]>([])
const selectedRows = ref<AssetItem[]>([])
const dialogVisible = ref(false)
const ownerDialogVisible = ref(false)
const ownerInput = ref('')
const editingRow = ref<AssetItem | null>(null)
const formRef = ref<FormInstance>()
const tableRef = ref<TableInstance>()
const sshKeys = ref<any[]>([])
const sshFilter = ref('')
const ordering = ref('risk')

const stats = reactive({ total: 0, active: 0, shutdown: 0, deleted: 0, sshReady: 0, sshMissing: 0 })

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
const form = reactive<AssetForm>(createAssetForm())

const validateIpAddress = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (!value) {
    callback(new Error('请输入 IP'))
    return
  }
  callback(isValidIpAddress(value) ? undefined : new Error('请输入正确的 IPv4 地址'))
}

const validateSshPort = (_rule: unknown, value: number, callback: (error?: Error) => void) => {
  const port = Number(value)
  callback(Number.isInteger(port) && port >= 1 && port <= 65535 ? undefined : new Error('端口范围为 1-65535'))
}

const rules: FormRules<AssetForm> = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip_address: [{ validator: validateIpAddress, trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  ssh_port: [{ validator: validateSshPort, trigger: 'change' }],
}

const activeRate = computed(() => {
  if (!stats.total) return ''
  return `${Math.round((stats.active / stats.total) * 100)}%`
})

const sshReadyRate = computed(() => {
  if (!stats.total) return ''
  return `${Math.round((stats.sshReady / stats.total) * 100)}%`
})

const cards = computed<{ key: CardKey; label: string; value: number; ratio: string; foot: string; dot: string; valueClass?: string }[]>(() => [
  { key: 'all', label: '主机总数', value: stats.total, ratio: '', foot: '资产库当前记录', dot: 'dot-info' },
  { key: 'active', label: '使用中', value: stats.active, ratio: activeRate.value, foot: '可纳入日常操作', dot: 'dot-success', valueClass: 'is-success' },
  { key: 'sshReady', label: 'SSH 就绪', value: stats.sshReady, ratio: sshReadyRate.value, foot: '密码或密钥认证可用', dot: 'dot-success' },
  { key: 'sshMissing', label: 'SSH 未配置', value: stats.sshMissing, ratio: '', foot: '点击查看待接入主机', dot: 'dot-danger', valueClass: 'is-danger' },
])

const activeCard = computed<CardKey>(() => {
  if (filters.status === '使用中') return 'active'
  if (sshFilter.value === 'ready') return 'sshReady'
  if (sshFilter.value === 'missing') return 'sshMissing'
  return 'all'
})

function toggleCard(key: CardKey) {
  if (key === 'all') {
    filters.status = ''
    sshFilter.value = ''
  } else if (key === 'active') {
    filters.status = filters.status === '使用中' ? '' : '使用中'
    sshFilter.value = ''
  } else if (key === 'sshReady') {
    sshFilter.value = sshFilter.value === 'ready' ? '' : 'ready'
    filters.status = ''
  } else {
    sshFilter.value = sshFilter.value === 'missing' ? '' : 'missing'
    filters.status = ''
  }
  applyFilters()
}

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

function completenessTip(row: AssetItem) {
  const missing = getAssetMissingFields(row)
  return missing.length ? `缺失：${missing.join('、')}，点击「编辑」补全` : '信息完整'
}

async function fetchStats() {
  try {
    const res: any = await getAssetStats()
    Object.assign(stats, {
      total: res.data.total ?? 0,
      active: res.data.active ?? 0,
      shutdown: res.data.shutdown ?? 0,
      deleted: res.data.deleted ?? 0,
      sshReady: res.data.ssh_ready ?? 0,
      sshMissing: res.data.ssh_missing ?? 0,
    })
  } catch { /* ignore */ }
}

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = {
      ...filters,
      ssh: sshFilter.value,
      ordering: ordering.value,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    }
    const res: any = await getAssets(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  resetPagination()
  fetchData()
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(() => filters.keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(applyFilters, 300)
})

function resetFilters() {
  Object.assign(filters, { keyword: '', asset_type: '', status: '' })
  sshFilter.value = ''
  ordering.value = 'risk'
  resetPagination()
  fetchData()
}

function refreshAll() {
  fetchStats()
  fetchData()
}

function handleSortChange({ prop, order }: { prop: string; order: 'ascending' | 'descending' | null }) {
  ordering.value = order ? (order === 'ascending' ? prop : `-${prop}`) : 'risk'
  applyFilters()
}

function handleSelectionChange(rows: AssetItem[]) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
}

function buildRowPayload(row: AssetItem, owner: string) {
  return {
    name: row.name,
    asset_type: row.asset_type,
    ip_address: row.ip_address,
    status: row.status,
    owner,
    description: row.description || '',
    spec: row.spec || '',
    os: row.os || '',
    ssh_port: row.ssh_port || 22,
    ssh_username: row.ssh_username || '',
    ssh_password: '',
    ssh_key_id: row.ssh_key_id ?? null,
  }
}

function openOwnerDialog() {
  ownerInput.value = ''
  ownerDialogVisible.value = true
}

async function submitBatchOwner() {
  const owner = ownerInput.value.trim()
  if (!owner) {
    ElMessage.warning('请输入负责人')
    return
  }
  batchLoading.value = true
  try {
    await Promise.all(selectedRows.value.map((row) => updateAsset(row.id, buildRowPayload(row, owner))))
    ElMessage.success(`已为 ${selectedRows.value.length} 台主机分配负责人`)
    ownerDialogVisible.value = false
    fetchData()
  } finally {
    batchLoading.value = false
  }
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 台主机？此操作不可恢复。`, '批量删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  batchLoading.value = true
  try {
    await Promise.all(selectedRows.value.map((row) => deleteAsset(row.id)))
    ElMessage.success('删除成功')
    clearSelection()
    fetchData()
    fetchStats()
  } finally {
    batchLoading.value = false
  }
}

function exportAssetsCsv(rows: AssetItem[], name: string) {
  if (!rows.length) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  const header = ['名称', 'IP 地址', '类型', '状态', '负责人', '规格', '操作系统', 'SSH 端口', 'SSH 用户名', '描述', '创建时间']
  const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = [header.join(',')]
  rows.forEach((row) => {
    lines.push([
      row.name,
      row.ip_address,
      row.asset_type,
      row.status,
      row.owner || '',
      row.spec || '',
      row.os || '',
      row.ssh_port || '',
      row.ssh_username || '',
      row.description || '',
      formatAssetDate(row.created_at),
    ].map(esc).join(','))
  })
  const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  link.href = url
  link.download = `${name}-${stamp}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function exportAll() {
  exporting.value = true
  try {
    const res: any = await getAssets({
      ...filters,
      ssh: sshFilter.value,
      ordering: ordering.value,
      page: 1,
      page_size: Math.max(total.value, 1),
    })
    exportAssetsCsv(res.data.items || [], '主机导出')
  } finally {
    exporting.value = false
  }
}

function exportSelected() {
  exportAssetsCsv(selectedRows.value, '主机导出-所选')
}

async function fetchSSHKeys() {
  try {
    const res: any = await getSSHKeys({ page_size: 100 })
    sshKeys.value = res.data?.items || []
  } catch { /* ignore */ }
}

async function fetchOwnerSuggestions(query: string, cb: (suggestions: { value: string }[]) => void) {
  try {
    const res: any = await getUsers({ keyword: query })
    const items: { value: string }[] = (res.data?.items || []).map((u: any) => ({
      value: u.full_name,
    }))
    cb(items)
  } catch {
    cb([])
  }
}

function showDialog(row?: AssetItem) {
  editingRow.value = row || null
  Object.assign(form, row ? createAssetFormFromAsset(row) : createAssetForm())
  fetchSSHKeys()
  dialogVisible.value = true
}

async function handleSave(keepOpen = false) {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingRow.value) {
      await updateAsset(editingRow.value.id, buildAssetPayload(form))
      ElMessage.success('更新成功')
      dialogVisible.value = false
    } else {
      await createAsset(buildAssetPayload(form))
      ElMessage.success('创建成功')
      if (keepOpen) {
        Object.assign(form, createAssetForm())
        formRef.value?.clearValidate()
      } else {
        dialogVisible.value = false
      }
    }
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

function goToSSHKeys() {
  dialogVisible.value = false
  router.push('/assets/ssh-keys')
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
.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: nowrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
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
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}

.metric-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgb(37 99 235 / 8%);
}

.metric-card.active {
  border-color: var(--primary-color);
  background: var(--primary-bg);
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

.metric-ratio {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 400;
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
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.filter-left {
  flex: 1;
  min-width: 0;
}

.filter-left :deep(.el-select) {
  flex: 0 0 132px;
  width: 132px;
}

.filter-right {
  flex: none;
  margin-left: auto;
}

.search-input {
  flex: 0 0 292px;
  width: 292px;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: var(--primary-bg);
  border: 1px solid #bfdbfe;
  border-radius: var(--border-radius);
  color: var(--primary-color);
  font-size: 13px;
}

.batch-bar-count b {
  font-weight: 700;
}

.batch-bar-spacer {
  flex: 1;
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

.form-divider {
  margin: 4px 0 16px;
}

.form-group--last {
  margin-bottom: 0;
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

.form-group-hint {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 400;
}

.auth-method-group,
.credential-form-item :deep(.el-select),
.credential-form-item :deep(.el-input) {
  width: 100%;
}

.credential-form-item {
  min-height: 32px;
}

.key-empty {
  padding: 8px 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.key-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.drawer-footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.owner-dialog-tip {
  margin: 0 0 10px;
  color: var(--text-secondary);
  font-size: 13px;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
    flex-basis: 100%;
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

  .drawer-footer {
    align-items: stretch;
    flex-direction: column-reverse;
  }

  .drawer-footer-right {
    width: 100%;
  }

  .drawer-footer-right :deep(.el-button) {
    flex: 1;
  }
}
</style>
