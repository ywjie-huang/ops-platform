<template>
  <div v-loading="loading">
    <!-- Header -->
    <div class="page-header" v-if="asset">
      <div style="display:flex;align-items:center;gap:12px">
        <el-button text @click="$router.push('/assets')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title" style="margin:0">{{ asset.name }}</h2>
        <el-tag :type="statusTagType(asset.status)" size="small" round>{{ asset.status }}</el-tag>
        <el-tag type="info" size="small">{{ asset.asset_type }}</el-tag>
        <span class="header-ip">{{ asset.ip_address }}</span>
      </div>
      <div style="display:flex;gap:8px">
        <el-button type="primary" @click="$router.push(`/monitoring/hosts/${assetId}/ssh`)">
          <el-icon><Monitor /></el-icon> SSH 连接
        </el-button>
        <el-button @click="openEdit">编辑</el-button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-body" v-if="asset">
      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="基础信息" name="basic">
          <div class="info-card">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">资产名称</div>
                <div class="info-value">{{ asset.name }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">资产类型</div>
                <div class="info-value">{{ asset.asset_type }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">IP 地址</div>
                <div class="info-value mono">{{ asset.ip_address }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">状态</div>
                <div class="info-value">
                  <el-tag :type="statusTagType(asset.status)" size="small" round>{{ asset.status }}</el-tag>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">负责人</div>
                <div class="info-value">{{ asset.owner || '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">创建时间</div>
                <div class="info-value">{{ asset.created_at }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">规格</div>
                <div class="info-value">{{ asset.spec || '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">操作系统</div>
                <div class="info-value">{{ asset.os || '-' }}</div>
              </div>
            </div>
            <div class="info-item full-width">
              <div class="info-label">说明</div>
              <div class="info-value">{{ asset.description || '-' }}</div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="连接配置" name="connection">
          <div class="info-card">
            <div class="info-grid triple">
              <div class="info-item">
                <div class="info-label">SSH 端口</div>
                <div class="info-value mono">{{ asset.ssh_port || 22 }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">用户名</div>
                <div class="info-value">{{ asset.ssh_username || 'root' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">认证方式</div>
                <div class="info-value">{{ authMethodLabel }}</div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="关联工单" name="tickets">
          <div class="info-card">
            <el-empty description="功能开发中" :image-size="80" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="变更记录" name="changelog">
          <div class="info-card">
            <el-empty description="功能开发中" :image-size="80" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" title="编辑资产" width="580px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="left">
        <div class="form-group">
          <div class="form-group-title"><span class="form-group-number">1</span> 基础信息</div>
          <div class="form-row">
            <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="类型" prop="asset_type">
              <el-select v-model="form.asset_type" style="width:100%">
                <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" /></el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width:100%">
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
          <div class="form-group-title"><span class="form-group-number">3</span> SSH 连接配置</div>
          <div class="form-row">
            <el-form-item label="端口"><el-input-number v-model="form.ssh_port" :min="1" :max="65535" style="width:100%" /></el-form-item>
            <el-form-item label="用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="认证方式">
              <el-select v-model="form.auth_method" style="width:100%">
                <el-option label="密码" value="password" />
                <el-option label="SSH 密钥" value="key" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="form.auth_method === 'password'" label="密码">
              <el-input v-model="form.ssh_password" type="password" show-password placeholder="留空则不修改" />
            </el-form-item>
            <el-form-item v-else label="SSH 密钥">
              <el-select v-model="form.ssh_key_id" placeholder="请选择 SSH 密钥" style="width:100%" clearable>
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
import { ref, reactive, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset, updateAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import { ElMessage, type FormInstance } from 'element-plus'
import { Monitor, ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const assetId = computed(() => Number(route.params.id))
const asset = ref<any>(null)
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
  return { '使用中': 'success', '已关机': 'warning', '已删除': 'info' }[status] || 'info'
}

const authMethodLabel = computed(() => {
  if (!asset.value) return '未配置'
  if (asset.value.ssh_key_id) {
    const key = sshKeys.value.find((k: any) => k.id === asset.value.ssh_key_id)
    return key ? `SSH 密钥（${key.name}）` : 'SSH 密钥'
  }
  if (asset.value.has_ssh_password) return '密码'
  return '未配置'
})

const form = reactive({
  name: '', asset_type: '云主机', ip_address: '', status: '使用中', owner: '', description: '',
  spec: '', os: '', ssh_port: 22, ssh_username: 'root', ssh_password: '',
  auth_method: 'password' as 'password' | 'key', ssh_key_id: null as number | null,
})
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip_address: [{ required: true, message: '请输入IP', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

async function fetchAsset() {
  loading.value = true
  try {
    const res: any = await getAsset(assetId.value)
    asset.value = res.data
  } finally { loading.value = false }
}

async function fetchSSHKeys() {
  try {
    const res: any = await getSSHKeys({ page_size: 100 })
    sshKeys.value = res.data?.items || []
  } catch { /* ignore */ }
}

function openEdit() {
  if (!asset.value) return
  const isKey = !!asset.value.ssh_key_id
  Object.assign(form, {
    name: asset.value.name,
    asset_type: asset.value.asset_type,
    ip_address: asset.value.ip_address,
    status: asset.value.status,
    owner: asset.value.owner || '',
    description: asset.value.description || '',
    spec: asset.value.spec || '',
    os: asset.value.os || '',
    ssh_port: asset.value.ssh_port || 22,
    ssh_username: asset.value.ssh_username || 'root',
    ssh_password: '',
    auth_method: isKey ? 'key' : 'password',
    ssh_key_id: asset.value.ssh_key_id || null,
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
    await updateAsset(assetId.value, payload)
    ElMessage.success('更新成功')
    dialogVisible.value = false
    fetchAsset()
  } finally { saving.value = false }
}

onActivated(() => { fetchAsset(); fetchSSHKeys() })
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.header-ip { font-size: 13px; color: var(--text-muted); font-family: monospace; }

.detail-body {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 0 24px 24px;
}

.info-card {
  background: var(--surface-color);
  border-radius: 8px;
  padding: 20px 0;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.info-grid.triple { grid-template-columns: 1fr 1fr 1fr; }
.info-item { padding: 8px 0; }
.info-item.full-width { margin-top: 8px; padding-top: 16px; border-top: 1px solid var(--border-color); }
.info-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.info-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.info-value.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

.form-group { margin-bottom: 20px; }
.form-group-title {
  font-size: 13px; font-weight: 600; color: var(--primary-color);
  margin-bottom: 12px; display: flex; align-items: center; gap: 6px;
}
.form-group-number {
  width: 18px; height: 18px; background: var(--primary-bg); border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center; font-size: 11px;
}
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.key-option { display: flex; align-items: center; justify-content: space-between; width: 100%; }
</style>
