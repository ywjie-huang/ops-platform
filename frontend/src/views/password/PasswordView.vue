<template>
  <div>
    <div class="page-header"><h2 class="page-title">修改密码</h2></div>
    <div class="data-card" style="max-width:480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">确认修改</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'; import { ElMessage, type FormInstance } from 'element-plus'; import { useRouter } from 'vue-router'
import request from '@/api/request'

const router = useRouter(); const formRef = ref<FormInstance>(); const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm_password: '' })
const rules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '至少6位', trigger: 'blur' }],
  confirm_password: [{ required: true, message: '请确认密码', trigger: 'blur' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await request.post('/password/', form)
    ElMessage.success('密码修改成功，请重新登录')
    localStorage.removeItem('ops_access_token')
    router.push('/login')
  } finally { loading.value = false }
}
</script>
