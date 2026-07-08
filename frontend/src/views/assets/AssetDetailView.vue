<template>
  <div v-loading="loading" class="asset-detail-page">
    <template v-if="asset">
      <div class="detail-header">
        <div>
          <div class="detail-title-row">
            <h1 class="detail-title">{{ asset.name }}</h1>
            <el-tag :type="statusTagType(asset.status)" size="small" round>{{ asset.status }}</el-tag>
            <el-tag size="small">{{ asset.asset_type }}</el-tag>
            <el-tag :type="sshTagType" size="small" round>{{ sshState.label }}</el-tag>
          </div>
          <div class="detail-fields">
            <div>
              <div class="field-label">主机 IP</div>
              <div class="field-value mono">{{ asset.ip_address }}</div>
            </div>
            <div>
              <div class="field-label">系统</div>
              <div class="field-value">{{ asset.os || '未填写' }}</div>
            </div>
            <div>
              <div class="field-label">负责人</div>
              <div class="field-value">{{ asset.owner || '未分配' }}</div>
            </div>
            <div>
              <div class="field-label">创建时间</div>
              <div class="field-value">{{ formatAssetDate(asset.created_at) }}</div>
            </div>
          </div>
        </div>
        <div class="detail-actions">
          <el-button :icon="ArrowLeft" @click="$router.push('/assets/list')">返回列表</el-button>
          <el-button :icon="EditPen" @click="openEdit">编辑</el-button>
          <el-button type="primary" :icon="Monitor" @click="$router.push(`/monitoring/hosts/${assetId}`)">
            查看监控
          </el-button>
        </div>
      </div>

      <div v-if="sshState.state !== 'key' && sshState.state !== 'password'" class="notice">
        <span class="status-dot dot-warning" />
        <span>当前主机 SSH 配置不完整，建议补齐用户名和密码或密钥后再作为批量执行、Web 终端目标。</span>
      </div>

      <div class="summary-grid">
        <div class="metric-card">
          <div class="metric-label">硬件规格</div>
          <div class="metric-value">{{ asset.spec || '未填写' }}</div>
          <div class="metric-foot">CPU / 内存 / 磁盘</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">操作系统</div>
          <div class="metric-value metric-text">{{ asset.os || '未填写' }}</div>
          <div class="metric-foot">系统版本</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">SSH 端口</div>
          <div class="metric-value mono">{{ asset.ssh_port || 22 }}</div>
          <div class="metric-foot">{{ asset.ssh_username || '未填写用户' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">关联入口</div>
          <div class="metric-value">4</div>
          <div class="metric-foot">监控、终端、批量、工单</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">SSH 状态</div>
          <div class="metric-value metric-text" :class="sshMetricClass">{{ sshState.label }}</div>
          <div class="metric-foot">连接就绪度</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">资产完整度</div>
          <div class="metric-value" :class="completenessTextClass">{{ completeness.percent }}%</div>
          <div class="metric-foot">基础、规格、SSH 信息</div>
        </div>
      </div>

      <div class="detail-grid">
        <div class="panel">
          <div class="panel-head">
            <h2 class="panel-title">资产信息</h2>
            <el-tag :type="completenessTagType" size="small">{{ completenessLabel }}</el-tag>
          </div>
          <el-tabs v-model="activeTab" class="detail-tabs">
            <el-tab-pane label="基础信息" name="basic">
              <div class="info-grid">
                <div class="info-item">
                  <div class="info-label">主机名称</div>
                  <div class="info-value">{{ asset.name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">IP 地址</div>
                  <div class="info-value mono">{{ asset.ip_address }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">资产类型</div>
                  <div class="info-value">{{ asset.asset_type }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">运行状态</div>
                  <div class="info-value">{{ asset.status }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">操作系统</div>
                  <div class="info-value">{{ asset.os || '-' }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">硬件规格</div>
                  <div class="info-value">{{ asset.spec || '-' }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">负责人</div>
                  <div class="info-value">{{ asset.owner || '-' }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">用途描述</div>
                  <div class="info-value">{{ asset.description || '-' }}</div>
                </div>
              </div>
              <div class="entry-grid" aria-label="相关入口">
                <button class="entry" type="button" @click="$router.push(`/monitoring/hosts/${assetId}`)">
                  <span class="entry-title">监控详情 <el-tag size="small" type="success">入口</el-tag></span>
                  <span class="entry-desc">查看 CPU、内存、磁盘和网络趋势。</span>
                </button>
                <button class="entry" type="button" @click="$router.push('/batch-exec')">
                  <span class="entry-title">批量执行 <el-tag size="small">入口</el-tag></span>
                  <span class="entry-desc">将该主机加入命令执行目标。</span>
                </button>
                <button class="entry" type="button" @click="$router.push('/tickets')">
                  <span class="entry-title">关联工单 <el-tag size="small" type="warning">查看</el-tag></span>
                  <span class="entry-desc">查看当前资产相关的问题和变更。</span>
                </button>
              </div>
            </el-tab-pane>

            <el-tab-pane label="连接配置" name="connection">
              <div class="info-grid triple">
                <div class="info-item">
                  <div class="info-label">SSH 端口</div>
                  <div class="info-value mono">{{ asset.ssh_port || 22 }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">用户名</div>
                  <div class="info-value">{{ asset.ssh_username || '未填写' }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">认证方式</div>
                  <div class="info-value">{{ authMethodLabel }}</div>
                </div>
              </div>
              <div class="config-actions">
                <el-button :icon="EditPen" @click="openEdit">编辑连接配置</el-button>
                <el-button type="primary" plain :disabled="sshState.state === 'missing'" @click="$router.push(`/monitoring/hosts/${assetId}/ssh`)">
                  打开 SSH 终端
                </el-button>
              </div>
            </el-tab-pane>

            <el-tab-pane label="关联工单" name="tickets">
              <div class="empty-panel">工单关联能力预留中，后续可在这里展示未关闭工单和变更申请。</div>
            </el-tab-pane>

            <el-tab-pane label="变更记录" name="changelog">
              <div class="empty-panel">变更记录能力预留中，后续可展示资产字段修改和 SSH 配置变更。</div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <aside class="panel">
          <div class="panel-head">
            <h2 class="panel-title">资产健康</h2>
            <el-tag :type="completenessTagType" size="small">{{ healthLabel }}</el-tag>
          </div>
          <div class="side-section">
            <div class="progress-row">
              <span>完整度</span>
              <strong :class="completenessTextClass">{{ completeness.percent }}%</strong>
            </div>
            <div class="progress-track">
              <span class="progress-bar" :class="completenessTone" :style="{ width: `${completeness.percent}%` }" />
            </div>
            <div class="check-list">
              <div class="check-item"><span>基础信息</span><el-tag size="small" type="success">完整</el-tag></div>
              <div class="check-item"><span>规格信息</span><el-tag size="small" :type="asset.spec && asset.os ? 'success' : 'warning'">{{ asset.spec && asset.os ? '完整' : '待补齐' }}</el-tag></div>
              <div class="check-item"><span>SSH 凭据</span><el-tag size="small" :type="sshTagType">{{ sshState.label }}</el-tag></div>
              <div class="check-item"><span>负责人</span><el-tag size="small" :type="asset.owner ? 'success' : 'warning'">{{ asset.owner ? '已分配' : '未分配' }}</el-tag></div>
            </div>
          </div>
          <div class="side-section">
            <div class="progress-row">
              <span>连接配置</span>
              <strong :class="sshMetricClass">{{ sshState.state === 'missing' ? 'Todo' : 'Ready' }}</strong>
            </div>
            <div class="check-list">
              <div class="check-item"><span>端口</span><span class="mono">{{ asset.ssh_port || 22 }}</span></div>
              <div class="check-item"><span>用户</span><span class="mono">{{ asset.ssh_username || '-' }}</span></div>
              <div class="check-item"><span>认证</span><span>{{ authMethodLabel }}</span></div>
              <div class="check-item"><span>凭据</span><span>{{ sshState.state === 'missing' ? '未保存' : '已保存' }}</span></div>
            </div>
          </div>
          <div class="side-section">
            <div class="progress-row">
              <span>建议动作</span>
              <strong>{{ suggestedActions.length }}</strong>
            </div>
            <div class="check-list">
              <div v-for="action in suggestedActions" :key="action.label" class="check-item">
                <span>{{ action.label }}</span>
                <el-button type="primary" link size="small" @click="action.run">{{ action.action }}</el-button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </template>

    <el-drawer
      v-model="dialogVisible"
      title="编辑主机"
      direction="rtl"
      size="560px"
      destroy-on-close
      class="asset-drawer"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="86px" label-position="left">
        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">1</span> 基础信息</div>
          <div class="form-row">
            <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="类型" prop="asset_type">
              <el-select v-model="form.asset_type" class="form-control">
                <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" /></el-form-item>
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
          <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        </div>
        <div class="form-group">
          <div class="form-group-title">
            <span class="form-group-number">3</span> SSH 连接配置
            <span class="form-group-hint">可选，可稍后补齐</span>
          </div>
          <div class="form-row">
            <el-form-item label="端口" prop="ssh_port"><el-input-number v-model="form.ssh_port" :min="1" :max="65535" controls-position="right" class="form-control" /></el-form-item>
            <el-form-item label="用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
          </div>
          <el-form-item label="认证方式">
            <el-radio-group v-model="form.auth_method" class="auth-method-group">
              <el-radio-button value="password">密码</el-radio-button>
              <el-radio-button value="key">SSH 密钥</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-show="form.auth_method === 'password'" label="密码" class="credential-form-item">
            <el-input v-model="form.ssh_password" type="password" show-password placeholder="留空则不修改" />
          </el-form-item>
          <el-form-item v-show="form.auth_method === 'key'" label="SSH 密钥" class="credential-form-item">
            <el-select v-model="form.ssh_key_id" placeholder="请选择 SSH 密钥" class="form-control" clearable>
              <template #empty>
                <div class="key-empty">
                  暂无密钥，<el-link type="primary" @click="goToSSHKeys">去创建</el-link>
                </div>
              </template>
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
      </el-form>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <div class="drawer-footer-right">
            <el-button :loading="saving" @click="handleSave(true)">保存并继续</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave(false)">保存</el-button>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, EditPen, Monitor } from '@element-plus/icons-vue'
import { getAsset, updateAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
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
  getAssetSshState,
  getCompletenessTone,
  type AssetLike,
} from '@/utils/assetDisplay'

type AssetDetail = AssetLike & {
  id: number
  name: string
  asset_type: string
  ip_address: string
  status: string
}
type TagType = 'success' | 'warning' | 'danger' | 'info'
type SuggestedAction = {
  label: string
  action: string
  run: () => void | Promise<unknown>
}

const route = useRoute()
const router = useRouter()
const assetId = computed(() => Number(route.params.id))
const asset = ref<AssetDetail | null>(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const activeTab = ref('basic')
const sshKeys = ref<any[]>([])

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

const sshState = computed(() => asset.value ? getAssetSshState(asset.value) : { state: 'missing' as const, label: '未配置', tone: 'danger' as const })
const completeness = computed(() => asset.value ? getAssetCompleteness(asset.value) : { completed: 0, total: 8, percent: 0 })
const completenessTone = computed(() => getCompletenessTone(completeness.value.percent))
const completenessTagType = computed<TagType>(() => completenessTone.value === 'danger' ? 'danger' : completenessTone.value)
const completenessTextClass = computed(() => `is-${completenessTone.value}`)
const completenessLabel = computed(() => completeness.value.percent >= 90 ? '已校验' : '待补齐')
const healthLabel = computed(() => completeness.value.percent >= 90 && sshState.value.state !== 'missing' ? '良好' : '关注')
const sshTagType = computed<TagType>(() => sshState.value.tone === 'danger' ? 'danger' : sshState.value.tone)
const sshMetricClass = computed(() => sshState.value.tone === 'success' ? 'is-success' : sshState.value.tone === 'warning' ? 'is-warning' : 'is-danger')

const authMethodLabel = computed(() => {
  if (!asset.value) return '未配置'
  if (asset.value.ssh_key_id) {
    const key = sshKeys.value.find((item: any) => item.id === asset.value?.ssh_key_id)
    return key ? `SSH 密钥：${key.name}` : 'SSH 密钥'
  }
  if (asset.value.has_ssh_password) return '密码'
  return '未配置'
})

const suggestedActions = computed<SuggestedAction[]>(() => {
  if (!asset.value) return []
  const actions: SuggestedAction[] = [
    { label: '查看监控趋势', action: '打开', run: () => router.push(`/monitoring/hosts/${assetId.value}`) },
    { label: '确认关联工单', action: '查看', run: () => router.push('/tickets') },
  ]
  if (sshState.value.state === 'missing' || sshState.value.state === 'partial') {
    actions.unshift({ label: '补齐 SSH 配置', action: '编辑', run: openEdit })
  } else {
    actions.unshift({ label: '打开 SSH 终端', action: '连接', run: () => router.push(`/monitoring/hosts/${assetId.value}/ssh`) })
  }
  if (!asset.value.owner || !asset.value.spec || !asset.value.os) {
    actions.push({ label: '补齐资产字段', action: '编辑', run: openEdit })
  }
  return actions
})

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

async function fetchAsset() {
  loading.value = true
  try {
    const res: any = await getAsset(assetId.value)
    asset.value = res.data
  } finally {
    loading.value = false
  }
}

async function fetchSSHKeys() {
  try {
    const res: any = await getSSHKeys({ page_size: 100 })
    sshKeys.value = res.data?.items || []
  } catch { /* ignore */ }
}

function openEdit() {
  if (!asset.value) return
  Object.assign(form, createAssetFormFromAsset(asset.value))
  fetchSSHKeys()
  dialogVisible.value = true
}

async function handleSave(keepOpen = false) {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await updateAsset(assetId.value, buildAssetPayload(form))
    ElMessage.success(keepOpen ? '已保存，可继续编辑' : '更新成功')
    if (!keepOpen) {
      dialogVisible.value = false
    }
    fetchAsset()
  } finally {
    saving.value = false
  }
}

function goToSSHKeys() {
  dialogVisible.value = false
  router.push('/assets/ssh-keys')
}

onActivated(() => {
  fetchAsset()
  fetchSSHKeys()
})
</script>

<style scoped>
.asset-detail-page {
  display: grid;
  gap: 12px;
}

.detail-header,
.notice,
.metric-card,
.panel {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.detail-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 14px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}

.detail-title {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
}

.detail-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.field-label,
.info-label {
  color: var(--text-muted);
  font-size: 12px;
}

.field-value,
.info-value {
  margin-top: 2px;
  color: var(--text-primary);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
}

.notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border-color: color-mix(in srgb, var(--warning-color), white 62%);
  background: color-mix(in srgb, var(--warning-color), white 92%);
  color: #6d4700;
  font-size: 13px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  flex: none;
}

.dot-warning { background: var(--warning-color); }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  padding: 12px 14px;
  min-width: 0;
}

.metric-label {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.metric-value {
  margin-top: 5px;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 750;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-text {
  font-size: 18px;
}

.metric-foot {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 12px;
}

.panel {
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.panel-title {
  margin: 0;
  font-size: 14px;
}

.detail-tabs {
  padding: 0 12px 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
  padding-top: 4px;
}

.info-grid.triple {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.info-item {
  min-width: 0;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  flex-wrap: wrap;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding-top: 12px;
}

.entry {
  min-height: 74px;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
  background: #fff;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.entry:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.entry-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 650;
}

.entry-desc {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.empty-panel {
  padding: 28px 0;
  color: var(--text-secondary);
  text-align: center;
}

.side-section {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.side-section:last-child {
  border-bottom: 0;
}

.progress-row,
.check-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.progress-row {
  align-items: baseline;
  margin-bottom: 7px;
}

.progress-row strong {
  color: var(--text-primary);
  font-size: 18px;
}

.progress-track {
  display: block;
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

.check-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.is-success { color: var(--success-color); }
.is-warning { color: var(--warning-color); }
.is-danger { color: var(--danger-color); }

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .entry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .detail-header {
    grid-template-columns: 1fr;
  }

  .detail-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-grid,
  .info-grid,
  .info-grid.triple,
  .entry-grid {
    grid-template-columns: 1fr;
  }

  .config-actions {
    justify-content: flex-start;
  }

  .config-actions :deep(.el-button) {
    flex: 1 1 160px;
  }
}

@media (max-width: 520px) {
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
