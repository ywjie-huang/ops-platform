<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">主机密钥</h2>
      <el-button type="primary" @click="showDialog()">+ 新增密钥</el-button>
    </div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索名称/用户名…" clearable style="width:220px" @keyup.enter="fetchData" />
      <el-button @click="fetchData">筛选</el-button>
      <el-button text @click="filters.keyword = ''; fetchData()">重置</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="密钥名称" min-width="160">
          <template #default="{row}">
            <div class="cell-stack">
              <span class="cell-primary">
                {{ row.name }}
                <el-tag v-if="row.is_default" type="success" size="small" style="margin-left:6px">默认</el-tag>
              </span>
              <span class="cell-secondary">{{ row.description || '无备注' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="认证方式" width="100">
          <template #default="{row}">
            <el-tag :type="row.auth_type === 'key' ? 'primary' : 'info'" size="small">
              {{ row.auth_type === 'key' ? '🔑 私钥' : '🔒 密码' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="100" />
        <el-table-column prop="port" label="端口" width="70" />
        <el-table-column label="凭据状态" width="120">
          <template #default="{row}">
            <span v-if="row.auth_type === 'key'" :class="row.has_private_key ? 'text-success' : 'text-muted'">
              {{ row.has_private_key ? '✓ 已配置私钥' : '✗ 未配置' }}
            </span>
            <span v-else :class="row.has_password ? 'text-success' : 'text-muted'">
              {{ row.has_password ? '✓ 已设置密码' : '✗ 未设置' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该密钥？关联的 SSH 连接将回退到资产自带凭据。" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
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

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑密钥' : '新增密钥'" width="600px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="密钥名称" prop="name">
          <el-input v-model="form.name" placeholder="如：生产环境通用密钥" />
        </el-form-item>
        <el-form-item label="认证类型" prop="auth_type">
          <el-radio-group v-model="form.auth_type">
            <el-radio value="password">密码认证</el-radio>
            <el-radio value="key">私钥认证</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="root" />
        </el-form-item>
        <el-form-item label="SSH 端口">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
        </el-form-item>

        <!-- 密码认证 -->
        <template v-if="form.auth_type === 'password'">
          <el-form-item label="SSH 密码" prop="password">
            <el-input v-model="form.password" type="password" show-password placeholder="请输入 SSH 密码" />
          </el-form-item>
        </template>

        <!-- 私钥认证 -->
        <template v-if="form.auth_type === 'key'">
          <el-form-item label="私钥内容" prop="private_key">
            <el-input v-model="form.private_key" type="textarea" :rows="6" placeholder="粘贴私钥内容（以 -----BEGIN 开头）" />
          </el-form-item>
          <el-form-item label="私钥密码">
            <el-input v-model="form.passphrase" type="password" show-password placeholder="如果私钥有密码保护请填写" />
          </el-form-item>
        </template>

        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选备注" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
          <span class="form-hint">默认密钥会在 SSH 连接时自动优先使用</span>
        </el-form-item>
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
import { getSSHKeys, getSSHKey, createSSHKey, updateSSHKey, deleteSSHKey } from '@/api/sshKeys'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage, type FormInstance } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const items = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)
const filters = reactive({ keyword: '' })

const form = reactive({
  name: '',
  auth_type: 'password',
  username: 'root',
  password: '',
  private_key: '',
  passphrase: '',
  port: 22,
  description: '',
  is_default: false,
})

const rules = {
  name: [{ required: true, message: '请输入密钥名称', trigger: 'blur' }],
  auth_type: [{ required: true, message: '请选择认证类型', trigger: 'change' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
}

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = {
      keyword: filters.keyword,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    }
    const res: any = await getSSHKeys(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function showDialog(row?: any) {
  editingId.value = row?.id || null
  if (row) {
    // 编辑模式：获取详情（含敏感字段）
    try {
      const res: any = await getSSHKey(row.id)
      const key = res.data
      Object.assign(form, {
        name: key.name,
        auth_type: key.auth_type,
        username: key.username,
        password: key.password || '',
        private_key: key.private_key || '',
        passphrase: key.passphrase || '',
        port: key.port,
        description: key.description || '',
        is_default: key.is_default,
      })
    } catch {
      ElMessage.error('获取密钥详情失败')
      return
    }
  } else {
    Object.assign(form, {
      name: '',
      auth_type: 'password',
      username: 'root',
      password: '',
      private_key: '',
      passphrase: '',
      port: 22,
      description: '',
      is_default: false,
    })
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  // 校验凭据
  if (form.auth_type === 'password' && !form.password && !editingId.value) {
    ElMessage.warning('请输入 SSH 密码')
    return
  }
  if (form.auth_type === 'key' && !form.private_key && !editingId.value) {
    ElMessage.warning('请粘贴私钥内容')
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      await updateSSHKey(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createSSHKey(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  await deleteSSHKey(id)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.cell-stack {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cell-primary {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
}
.cell-secondary {
  font-size: 12px;
  color: var(--text-muted);
}
.text-success { color: var(--el-color-success); font-size: 13px; }
.text-muted { color: var(--text-muted); font-size: 13px; }
.form-hint { margin-left: 8px; font-size: 12px; color: var(--text-muted); }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
