<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">角色权限</h2>
      <el-button type="primary" @click="showRoleDialog()">+ 新增角色</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="角色名称">
          <template #default="{row}"><strong>{{ row.name }}</strong> <el-tag v-if="row.is_system" size="small">系统</el-tag></template>
        </el-table-column>
        <el-table-column prop="code" label="编码"><template #default="{row}"><code>{{ row.code }}</code></template></el-table-column>
        <el-table-column label="权限数"><template #default="{row}">{{ row.permissions?.length || 0 }}</template></el-table-column>
        <el-table-column prop="description" label="说明" />
        <el-table-column label="操作" width="220">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="showRoleDialog(row)">修改</el-button>
            <el-button size="small" text :type="row.code === 'super_admin' ? 'info' : 'primary'" :disabled="row.code === 'super_admin'" @click="showPermDialog(row)">分配菜单</el-button>
            <el-popconfirm v-if="!row.is_system && !row.user_count" title="确认删除？" @confirm="handleDeleteRole(row.id)">
              <template #reference><el-button size="small" text type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 角色弹窗 -->
    <el-dialog v-model="roleDialogVisible" :title="editingId ? '修改角色' : '新增角色'" width="480px">
      <el-form ref="roleFormRef" :model="roleForm" :rules="roleRules" label-width="80px">
        <el-form-item label="角色名称" prop="name"><el-input v-model="roleForm.name" /></el-form-item>
        <el-form-item label="角色编码" prop="code"><el-input v-model="roleForm.code" :disabled="!!editingId" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="roleForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveRole">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分配菜单弹窗 -->
    <el-dialog v-model="permDialogVisible" title="分配菜单" width="860px">
      <div class="perm-info">
        <el-icon><InfoFilled /></el-icon>
        <span>普通用户 {{ permRoleName }} - 菜单分配后需要用户手动刷新页面才会生效</span>
      </div>
      <div class="perm-batch">
        <span class="batch-label">全选操作</span>
        <el-button size="small" @click="batchPerm('all', true)">全部</el-button>
        <el-button size="small" @click="batchPerm('view', true)">查询</el-button>
        <el-button size="small" @click="batchPerm('create', true)">新增</el-button>
        <el-button size="small" @click="batchPerm('update', true)">修改</el-button>
        <el-button size="small" @click="batchPerm('delete', true)">删除</el-button>
        <span class="batch-label" style="margin-left:16px">反选操作</span>
        <el-button size="small" @click="batchPerm('all', false)">全部</el-button>
        <el-button size="small" @click="batchPerm('view', false)">查询</el-button>
        <el-button size="small" @click="batchPerm('create', false)">新增</el-button>
        <el-button size="small" @click="batchPerm('update', false)">修改</el-button>
        <el-button size="small" @click="batchPerm('delete', false)">删除</el-button>
      </div>
      <div class="perm-tree">
        <div v-for="group in permTree" :key="group.parent" class="perm-group">
          <div class="perm-group-header">
            <el-checkbox :model-value="isParentChecked(group)" :indeterminate="isParentIndeterminate(group)" @change="toggleParent(group, $event)">
              <strong>{{ group.parent }}</strong>
            </el-checkbox>
          </div>
          <div v-for="child in group.children" :key="child.module" class="perm-child-row">
            <div class="perm-child-label">
              <el-checkbox :model-value="isChildChecked(child)" :indeterminate="isChildIndeterminate(child)" @change="toggleChild(child, $event)">
                {{ child.label }}
              </el-checkbox>
            </div>
            <div class="perm-func-list">
              <el-checkbox v-for="p in child.permissions" :key="p.id" :model-value="permChecked.has(p.id)" @change="togglePerm(p, $event)">
                {{ p.name }}
              </el-checkbox>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSavePerm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getRoles, createRole, updateRole, deleteRole, assignPermissions, getPermissionTree } from '@/api/roles'
import { ElMessage, type FormInstance } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

const loading = ref(false); const saving = ref(false)
const items = ref<any[]>([])
const roleDialogVisible = ref(false); const editingId = ref<number | null>(null)
const roleFormRef = ref<FormInstance>()
const roleForm = reactive({ name: '', code: '', description: '' })
const roleRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
}

// 权限分配
const permDialogVisible = ref(false)
const permRoleId = ref(0)
const permRoleName = ref('')
const permTree = ref<any[]>([])
const permChecked = ref(new Set<number>())
const permMap = new Map<number, any>() // id -> perm

async function fetchData() {
  loading.value = true
  try { const res: any = await getRoles(); items.value = res.data.items } finally { loading.value = false }
}

function showRoleDialog(row?: any) {
  editingId.value = row?.id || null
  Object.assign(roleForm, row ? { name: row.name, code: row.code, description: row.description } : { name: '', code: '', description: '' })
  roleDialogVisible.value = true
}

async function handleSaveRole() {
  if (!editingId.value) {
    const valid = await roleFormRef.value?.validate().catch(() => false)
    if (!valid) return
  }
  saving.value = true
  try {
    if (editingId.value) { await updateRole(editingId.value, roleForm); ElMessage.success('更新成功') }
    else { await createRole(roleForm); ElMessage.success('创建成功') }
    roleDialogVisible.value = false; fetchData()
  } finally { saving.value = false }
}

async function handleDeleteRole(id: number) { await deleteRole(id); ElMessage.success('删除成功'); fetchData() }

async function showPermDialog(row: any) {
  permRoleId.value = row.id
  permRoleName.value = row.name
  permChecked.value = new Set(row.permissions.map((p: any) => p.id))
  permMap.clear()
  if (!permTree.value.length) {
    const res: any = await getPermissionTree()
    permTree.value = res.data
  }
  permTree.value.forEach(g => g.children.forEach((c: any) => c.permissions.forEach((p: any) => permMap.set(p.id, p))))
  permDialogVisible.value = true
}

function isParentChecked(group: any) {
  return group.children.every((c: any) => c.permissions.every((p: any) => permChecked.value.has(p.id)))
}
function isParentIndeterminate(group: any) {
  const ids = group.children.flatMap((c: any) => c.permissions.map((p: any) => p.id))
  const checked = ids.filter((id: number) => permChecked.value.has(id)).length
  return checked > 0 && checked < ids.length
}
function toggleParent(group: any, val: boolean) {
  group.children.forEach((c: any) => c.permissions.forEach((p: any) => {
    if (val) permChecked.value.add(p.id); else permChecked.value.delete(p.id)
  }))
}
function isChildChecked(child: any) { return child.permissions.every((p: any) => permChecked.value.has(p.id)) }
function isChildIndeterminate(child: any) {
  const checked = child.permissions.filter((p: any) => permChecked.value.has(p.id)).length
  return checked > 0 && checked < child.permissions.length
}
function toggleChild(child: any, val: boolean) {
  child.permissions.forEach((p: any) => { if (val) permChecked.value.add(p.id); else permChecked.value.delete(p.id) })
}
function togglePerm(perm: any, val: boolean) {
  if (val) permChecked.value.add(perm.id); else permChecked.value.delete(perm.id)
}

function batchPerm(action: string, check: boolean) {
  const ids = action === 'all'
    ? Array.from(permMap.keys())
    : Array.from(permMap.values()).filter((p: any) => p.code.split('.')[1] === action).map((p: any) => p.id)
  ids.forEach(id => { if (check) permChecked.value.add(id); else permChecked.value.delete(id) })
}

async function handleSavePerm() {
  saving.value = true
  try {
    await assignPermissions(permRoleId.value, Array.from(permChecked.value))
    ElMessage.success('权限分配成功')
    permDialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.perm-info {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: var(--primary-bg); color: #1d4ed8;
  font-size: 13px; border-radius: 6px; margin-bottom: 12px;
}
.perm-batch {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 10px 0; margin-bottom: 12px;
  .batch-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
}
.perm-tree { max-height: 50vh; overflow-y: auto; }
.perm-group { margin-bottom: 8px; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
.perm-group-header { padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid var(--border-color); }
.perm-child-row { display: flex; border-bottom: 1px solid var(--border-color); &:last-child { border-bottom: none; } }
.perm-child-label { width: 160px; padding: 8px 14px; border-right: 1px solid var(--border-color); display: flex; align-items: center; font-size: 13px; }
.perm-func-list { flex: 1; padding: 8px 14px; display: flex; flex-wrap: wrap; gap: 4px 16px; align-items: center; }
</style>
