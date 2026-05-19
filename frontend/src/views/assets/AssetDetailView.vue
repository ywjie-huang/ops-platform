<template>
  <div>
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <el-button text @click="$router.back()">← 返回</el-button>
        <h2 class="page-title" style="margin:0">资产详情</h2>
      </div>
      <el-button type="primary" @click="openEdit">编辑</el-button>
    </div>

    <div class="data-card" v-loading="loading" v-if="asset">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="名称"><strong>{{ asset.name }}</strong></el-descriptions-item>
        <el-descriptions-item label="类型">{{ asset.asset_type }}</el-descriptions-item>
        <el-descriptions-item label="IP">{{ asset.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="{ '使用中': 'success', '已关机': 'warning', '已删除': 'info' }[asset.status] || 'info'" round>{{ asset.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="规格">{{ asset.spec || '-' }}</el-descriptions-item>
        <el-descriptions-item label="系统">{{ asset.os || '-' }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ asset.owner || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ asset.created_at }}</el-descriptions-item>
        <el-descriptions-item label="说明" :span="2">{{ asset.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="SSH 端口">{{ asset.ssh_port || 22 }}</el-descriptions-item>
        <el-descriptions-item label="SSH 用户名">{{ asset.ssh_username || 'root' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" title="编辑资产" width="580px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" prop="asset_type">
          <el-select v-model="form.asset_type" style="width:100%">
            <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" /></el-form-item>
        <el-form-item label="规格"><el-input v-model="form.spec" placeholder="如 4C8G" /></el-form-item>
        <el-form-item label="系统"><el-input v-model="form.os" placeholder="如 Ubuntu 22.04" /></el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-divider content-position="left">SSH 配置</el-divider>
        <el-form-item label="SSH 端口"><el-input-number v-model="form.ssh_port" :min="1" :max="65535" style="width:100%" /></el-form-item>
        <el-form-item label="SSH 用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
        <el-form-item label="SSH 密码"><el-input v-model="form.ssh_password" type="password" show-password placeholder="留空则不修改" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset, updateAsset } from '@/api/assets'
import { ElMessage, type FormInstance } from 'element-plus'

const route = useRoute()
const assetId = Number(route.params.id)
const asset = ref<any>(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const assetTypes = ['云主机', '数据库', '网络设备', '中间件', '其他']
const statusList = [
  { label: '使用中', value: '使用中' },
  { label: '已关机', value: '已关机' },
  { label: '已删除', value: '已删除' },
]

const form = reactive({
  name: '', asset_type: '云主机', ip_address: '', status: '使用中', owner: '', description: '',
  spec: '', os: '', ssh_port: 22, ssh_username: 'root', ssh_password: '',
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
    const res: any = await getAsset(assetId)
    asset.value = res.data
  } finally { loading.value = false }
}

function openEdit() {
  if (!asset.value) return
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
  })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await updateAsset(assetId, form)
    ElMessage.success('更新成功')
    dialogVisible.value = false
    fetchAsset()
  } finally { saving.value = false }
}

onMounted(fetchAsset)
</script>

<style scoped>
.data-card { background: #fff; border-radius: 8px; padding: 24px; }
</style>
