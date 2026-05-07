<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <el-button type="primary" @click="showDialog()">+ 新增用户</el-button>
    </div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索用户名、姓名…" clearable style="width:220px" @keyup.enter="fetchData" />
      <el-select v-model="filters.role_id" placeholder="全部角色" clearable style="width:150px" @change="fetchData">
        <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名"><template #default="{row}"><strong>{{ row.username }}</strong></template></el-table-column>
        <el-table-column prop="full_name" label="姓名" />
        <el-table-column label="角色">
          <template #default="{row}">
            <el-tag v-for="r in row.roles" :key="r.id" size="small" style="margin-right:4px">{{ r.name }}</el-tag>
            <span v-if="!row.roles?.length" class="text-muted">未分配</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="showDialog(row)">修改</el-button>
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" text type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '修改用户' : '新增用户'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="姓名" prop="full_name"><el-input v-model="form.full_name" /></el-form-item>
        <el-form-item :label="editingId ? '新密码' : '密码'" :prop="editingId ? '' : 'password'">
          <el-input v-model="form.password" type="password" :placeholder="editingId ? '留空则不修改' : '至少6位'" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox-group v-model="form.role_ids">
            <el-checkbox v-for="r in roles" :key="r.id" :label="r.id">{{ r.name }}</el-checkbox>
          </el-checkbox-group>
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
import { getUsers, createUser, updateUser, deleteUser, getUserRoles } from '@/api/users'
import { ElMessage, type FormInstance } from 'element-plus'

const loading = ref(false); const saving = ref(false)
const items = ref<any[]>([]); const roles = ref<any[]>([])
const dialogVisible = ref(false); const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const filters = reactive({ keyword: '', role_id: '' })
const form = reactive({ username: '', full_name: '', password: '', role_ids: [] as number[] })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  full_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try { const res: any = await getUsers(filters); items.value = res.data.items } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || null
  Object.assign(form, row ? { username: row.username, full_name: row.full_name, password: '', role_ids: row.roles.map((r: any) => r.id) } : { username: '', full_name: '', password: '', role_ids: [] })
  dialogVisible.value = true
}

async function handleSave() {
  if (!editingId.value) {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
  }
  saving.value = true
  try {
    if (editingId.value) { await updateUser(editingId.value, form); ElMessage.success('更新成功') }
    else { await createUser(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; fetchData()
  } finally { saving.value = false }
}

async function handleDelete(id: number) { await deleteUser(id); ElMessage.success('删除成功'); fetchData() }

onMounted(async () => {
  const res: any = await getUserRoles(); roles.value = res.data
  fetchData()
})
</script>

<style scoped>.text-muted { color: var(--text-muted); font-size: 13px; }</style>
