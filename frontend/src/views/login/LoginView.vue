<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
      <div class="shape shape-4"></div>
      <div class="shape shape-5"></div>
    </div>

    <!-- 左侧品牌区域 -->
    <div class="brand-section">
      <div class="brand-content">
        <div class="brand-icon">
          <el-icon :size="48"><Monitor /></el-icon>
        </div>
        <h1 class="brand-title">运维管理平台</h1>
        <p class="brand-desc">一站式基础设施监控与运维管理解决方案</p>
        <div class="brand-features">
          <div class="feature-item">
            <el-icon><DataLine /></el-icon>
            <span>实时监控告警</span>
          </div>
          <div class="feature-item">
            <el-icon><Box /></el-icon>
            <span>资产容器管理</span>
          </div>
          <div class="feature-item">
            <el-icon><Document /></el-icon>
            <span>工单协作流转</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="form-section">
      <div class="login-card">
        <h2>欢迎回来</h2>
        <p class="subtitle">登录您的账户以继续</p>
        <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item prop="captcha_code">
            <div class="captcha-row">
              <el-input
                v-model="form.captcha_code"
                placeholder="请输入验证码"
                :prefix-icon="Key"
                size="large"
                @keyup.enter="handleLogin"
              />
              <img
                v-if="captchaUrl"
                :src="captchaUrl"
                alt="验证码"
                class="captcha-img"
                @click="refreshCaptcha"
                title="点击刷新"
              />
              <div v-else class="captcha-img captcha-placeholder" @click="refreshCaptcha">加载中</div>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              @click="handleLogin"
            >
              <span v-if="!loading">登 录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form-item>
        </el-form>
        <div class="footer-text">
          <span>Powered by Ops Platform</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/modules/auth'
import { getCaptcha } from '@/api/auth'
import { Monitor, DataLine, Box, Document, User, Lock, Key } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const captchaId = ref('')
const captchaUrl = ref('')
const form = reactive({ username: '', password: '', captcha_code: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function refreshCaptcha() {
  try {
    if (captchaUrl.value) URL.revokeObjectURL(captchaUrl.value)
    const { captchaId: id, imageUrl } = await getCaptcha()
    captchaId.value = id
    captchaUrl.value = imageUrl
    form.captcha_code = ''
  } catch {
    ElMessage.error('获取验证码失败')
  }
}

onMounted(refreshCaptcha)

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(form.username, form.password, captchaId.value, form.captcha_code)
    await authStore.fetchUserInfo()
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    refreshCaptcha()
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  background: #0f172a;
  position: relative;
  overflow: hidden;
}

/* ─── 背景动态装饰 ─── */
.bg-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.08;
  animation: float 20s ease-in-out infinite;
}

.shape-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  top: -200px;
  right: -100px;
  animation-delay: 0s;
}

.shape-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  bottom: -150px;
  left: -100px;
  animation-delay: -5s;
}

.shape-3 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #8b5cf6, #ec4899);
  top: 40%;
  left: 30%;
  animation-delay: -10s;
}

.shape-4 {
  width: 150px;
  height: 150px;
  background: linear-gradient(135deg, #10b981, #06b6d4);
  top: 20%;
  right: 25%;
  animation-delay: -7s;
}

.shape-5 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #f59e0b, #ef4444);
  bottom: 10%;
  right: 10%;
  animation-delay: -12s;
  opacity: 0.05;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(-20px, 30px) scale(0.95); }
  75% { transform: translate(15px, 15px) scale(1.02); }
}

/* ─── 左侧品牌 ─── */
.brand-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  z-index: 1;
}

.brand-content {
  max-width: 440px;
  color: #e2e8f0;
}

.brand-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 24px;
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 12px;
  letter-spacing: -0.5px;
}

.brand-desc {
  font-size: 16px;
  color: #94a3b8;
  margin: 0 0 40px;
  line-height: 1.6;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: #cbd5e1;

  .el-icon {
    font-size: 20px;
    color: #60a5fa;
  }
}

/* ─── 右侧表单 ─── */
.form-section {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  z-index: 1;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 40px 32px 28px;

  h2 {
    font-size: 26px;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 8px;
  }

  .subtitle {
    color: #64748b;
    font-size: 14px;
    margin: 0 0 32px;
  }
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  box-shadow: none;
  transition: all 0.3s;

  &:hover,
  &.is-focus {
    border-color: rgba(96, 165, 250, 0.5);
    background: rgba(255, 255, 255, 0.08);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
}

:deep(.el-input__inner) {
  color: #e2e8f0;
  font-size: 14px;

  &::placeholder {
    color: #475569;
  }
}

:deep(.el-input__prefix .el-icon) {
  color: #64748b;
}

.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
  margin-top: 8px;
  transition: all 0.3s;

  &:hover {
    background: linear-gradient(135deg, #2563eb, #4f46e5);
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35);
  }

  &:active {
    transform: translateY(0);
  }
}

.captcha-row {
  display: flex;
  gap: 12px;
  width: 100%;

  .el-input { flex: 1; }
}

.captcha-img {
  height: 40px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: border-color 0.3s;

  &:hover { border-color: rgba(96, 165, 250, 0.5); }
}

.captcha-placeholder {
  width: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
}

.footer-text {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  color: #334155;
}

/* ─── 响应式 ─── */
@media (max-width: 900px) {
  .login-page {
    flex-direction: column;
  }

  .brand-section {
    padding: 40px 24px 20px;
  }

  .brand-content {
    text-align: center;
  }

  .brand-icon {
    margin: 0 auto 16px;
  }

  .brand-title {
    font-size: 26px;
  }

  .brand-features {
    flex-direction: row;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
  }

  .form-section {
    width: 100%;
    padding: 20px;
  }
}
</style>
