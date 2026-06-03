<template>
  <div class="header">
    <div class="header-left">
      <div class="toggle-btn" @click="appStore.toggleSidebar">
        <el-icon :size="16"><Fold /></el-icon>
      </div>
      <input
        class="search-input"
        type="text"
        placeholder="搜索主机、容器、工单…"
        readonly
        @click="handleSearchClick"
      />
    </div>
    <div class="header-right">
      <el-dropdown trigger="click">
        <div class="user-avatar">{{ authStore.fullName?.[0] || 'U' }}</div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="pwdVisible = true">修改密码</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>

  <!-- 修改密码弹窗 -->
  <el-dialog v-model="pwdVisible" title="修改密码" width="420px" destroy-on-close>
    <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px">
      <el-form-item label="当前密码" prop="old_password">
        <el-input v-model="pwdForm.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="pwdForm.new_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input v-model="pwdForm.confirm_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwdVisible = false">取消</el-button>
      <el-button type="primary" :loading="pwdLoading" @click="handleChangePwd">确认修改</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/modules/app'
import { useAuthStore } from '@/stores/modules/auth'
import { Fold } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance } from 'element-plus'
import request from '@/api/request'

const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

function handleSearchClick() {
  // TODO: 后续实现命令面板 (⌘K)
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

// 修改密码
const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const pwdRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少6位', trigger: 'blur' },
  ],
  confirm_password: [{ required: true, message: '请确认密码', trigger: 'blur' }],
}

async function handleChangePwd() {
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return
  pwdLoading.value = true
  try {
    await request.post('/password/', pwdForm)
    ElMessage.success('密码修改成功，请重新登录')
    localStorage.removeItem('ops_access_token')
    router.push('/login')
  } finally { pwdLoading.value = false }
}
</script>

<style lang="scss" scoped>
.header {
  height: 44px;
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.12s;
  flex-shrink: 0;

  &:hover {
    background: #f5f5f5;
    color: var(--text-secondary);
  }
}

.search-input {
  background: #f5f5f5;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 6px 12px 6px 32px;
  font-size: 12px;
  color: var(--text-secondary);
  width: 240px;
  outline: none;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: 10px center;

  &:focus {
    border-color: #5e6ad2;
  }

  &::placeholder {
    color: var(--text-muted);
  }
}

.header-right {
  display: flex;
  align-items: center;
}

.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #5e6ad2;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  cursor: pointer;
}
</style>
