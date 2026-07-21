<template>
  <main class="login-page">
    <div class="shell">
      <section class="brand-pane" aria-labelledby="brand-title">
        <div class="brand-intro">
          <div class="brand-kicker">
            <span class="brand-mark" aria-hidden="true">
              <span class="icon">
                <svg viewBox="0 0 24 24">
                  <path d="M4 5h16v10H4z" />
                  <path d="M8 19h8" />
                  <path d="M12 15v4" />
                </svg>
              </span>
            </span>
            Ops Platform
          </div>
          <h1 id="brand-title" class="brand-title">运维管理平台</h1>
          <p class="brand-copy">
            统一处理主机监控、告警事件、容器运维、批量执行与应用发布。
            登录后进入值班工作台。
          </p>
        </div>

        <div class="ops-board" aria-label="运维拓扑示意">
          <div class="ops-board-header">
            <div class="board-title">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M12 3v18" />
                  <path d="M3 12h18" />
                  <path d="m5 5 14 14" />
                  <path d="m19 5-14 14" />
                </svg>
              </span>
              运维拓扑
            </div>
            <div class="board-note">示意接入关系，非实时状态</div>
          </div>

          <div class="topology-wrap">
            <svg class="topology" viewBox="0 0 850 320" preserveAspectRatio="none" aria-hidden="true">
              <path class="topology-line" d="M170 78 C255 64 320 118 420 140" />
              <path class="topology-line is-warning" d="M680 78 C600 64 525 118 430 140" />
              <path class="topology-line is-blue" d="M210 250 C285 210 340 180 420 152" />
              <path class="topology-line" d="M650 250 C580 210 520 180 430 152" />
            </svg>

            <div class="node node-core">
              <div class="node-title">
                Ops Core
                <span class="node-badge">核心</span>
              </div>
              <div class="node-meta">API · 权限 · 审计</div>
            </div>

            <div class="node node-prometheus">
              <div class="node-title">
                Prometheus
                <span class="node-badge">监控</span>
              </div>
              <div class="node-meta">主机指标采集</div>
            </div>

            <div class="node node-alert">
              <div class="node-title">
                Alertmanager
                <span class="node-badge is-warning">告警</span>
              </div>
              <div class="node-meta">规则与事件</div>
            </div>

            <div class="node node-k8s">
              <div class="node-title">
                K8s
                <span class="node-badge is-info">集群</span>
              </div>
              <div class="node-meta">资源发现</div>
            </div>

            <div class="node node-docker">
              <div class="node-title">
                Docker Agent
                <span class="node-badge">容器</span>
              </div>
              <div class="node-meta">主机侧代理</div>
            </div>
          </div>
        </div>

        <div class="capability-row" aria-label="平台能力">
          <div class="capability">
            <span class="capability-icon" aria-hidden="true">
              <span class="icon">
                <svg viewBox="0 0 24 24">
                  <path d="M4 19V5" />
                  <path d="M4 19h16" />
                  <path d="m7 15 4-4 3 3 5-7" />
                </svg>
              </span>
            </span>
            监控告警
          </div>
          <div class="capability">
            <span class="capability-icon" aria-hidden="true">
              <span class="icon">
                <svg viewBox="0 0 24 24">
                  <path d="M21 16V8l-9-5-9 5v8l9 5z" />
                  <path d="M3.3 7.2 12 12l8.7-4.8" />
                  <path d="M12 22V12" />
                </svg>
              </span>
            </span>
            资产容器
          </div>
          <div class="capability">
            <span class="capability-icon" aria-hidden="true">
              <span class="icon">
                <svg viewBox="0 0 24 24">
                  <path d="M7 8h10" />
                  <path d="M7 12h6" />
                  <path d="M9 20h6" />
                  <path d="M12 16v4" />
                  <path d="M5 4h14v12H5z" />
                </svg>
              </span>
            </span>
            批量执行
          </div>
          <div class="capability">
            <span class="capability-icon" aria-hidden="true">
              <span class="icon">
                <svg viewBox="0 0 24 24">
                  <path d="M4 4h16v16H4z" />
                  <path d="M8 9h8" />
                  <path d="M8 13h6" />
                  <path d="M8 17h4" />
                </svg>
              </span>
            </span>
            工单发布
          </div>
        </div>

        <div class="brand-footer">
          <span>登录后查看实时资产、告警与巡检态势</span>
          <span class="env-pill">内部环境</span>
        </div>
      </section>

      <section class="login-pane" aria-labelledby="login-title">
        <div class="login-head">
          <div class="login-secure">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d="M12 3 5 6v6c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.8 7-9V6z" />
                <path d="m9 12 2 2 4-4" />
              </svg>
            </span>
            安全入口
          </div>
          <h2 id="login-title" class="login-title">登录</h2>
          <p class="login-copy">使用平台账号进入值班工作台</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
          aria-label="登录表单"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username" label="账号">
            <el-input
              ref="usernameRef"
              v-model="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              size="large"
              autocomplete="username"
              aria-label="账号"
              :disabled="loading"
            />
          </el-form-item>

          <el-form-item prop="password" label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              size="large"
              autocomplete="current-password"
              show-password
              aria-label="密码"
              :disabled="loading"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item prop="captcha_code" label="验证码">
            <div class="captcha-row">
              <el-input
                ref="captchaRef"
                v-model="form.captcha_code"
                placeholder="请输入验证码"
                :prefix-icon="Key"
                size="large"
                inputmode="numeric"
                aria-label="验证码"
                :disabled="loading"
                @keyup.enter="handleLogin"
              />
              <button
                class="captcha-button"
                type="button"
                aria-label="刷新验证码"
                title="点击刷新验证码"
                :disabled="loading || captchaLoading"
                @click="refreshCaptcha()"
              >
                <img
                  v-if="captchaUrl"
                  :src="captchaUrl"
                  alt="验证码"
                  class="captcha-img"
                />
                <span v-else class="captcha-placeholder">{{ captchaLoading ? '加载中' : '点击刷新' }}</span>
              </button>
            </div>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            native-type="submit"
            :loading="loading"
            class="login-button"
            aria-label="登录"
            @click="handleLogin"
          >
            <span v-if="!loading">登录</span>
            <span v-else>登录中...</span>
          </el-button>

          <div class="session-row" aria-label="登录安全信息">
            <span>会话将在登录后由服务端签发</span>
            <span>权限由 RBAC 控制</span>
          </div>
        </el-form>

        <div class="login-panel-bottom">
          <span>Ops Platform</span>
          <span>内部运维入口</span>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/modules/auth'
import { getCaptcha } from '@/api/auth'
import { User, Lock, Key } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type InputInstance } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const usernameRef = ref<InputInstance>()
const captchaRef = ref<InputInstance>()
const loading = ref(false)
const captchaLoading = ref(false)

const captchaId = ref('')
const captchaUrl = ref('')
const form = reactive({ username: '', password: '', captcha_code: '' })
const rules = {
  username: [{ required: true, message: '用户名不能为空', trigger: 'blur' }],
  password: [{ required: true, message: '密码不能为空', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

function safeRedirectPath(raw: unknown): string {
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) {
    return '/'
  }
  return raw
}

async function refreshCaptcha(options?: { focus?: boolean }) {
  captchaLoading.value = true
  try {
    if (captchaUrl.value) URL.revokeObjectURL(captchaUrl.value)
    const { captchaId: id, imageUrl } = await getCaptcha()
    captchaId.value = id
    captchaUrl.value = imageUrl
    form.captcha_code = ''
    if (options?.focus) {
      await nextTick()
      captchaRef.value?.focus()
    }
  } catch {
    ElMessage.error('获取验证码失败')
  } finally {
    captchaLoading.value = false
  }
}

onMounted(async () => {
  await refreshCaptcha()
  await nextTick()
  usernameRef.value?.focus()
})

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(form.username, form.password, captchaId.value, form.captcha_code)
    await authStore.fetchUserInfo()
    ElMessage.success('登录成功')
    router.push(safeRedirectPath(route.query.redirect))
  } catch {
    await refreshCaptcha({ focus: true })
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  --login-surface: #0d1713;
  --login-surface-strong: #111d18;
  --login-surface-muted: #0a120e;
  --login-border: #1c3028;
  --login-border-strong: #2f5a49;
  --login-text-primary: #f2fff8;
  --login-text-secondary: #a9c4b8;
  --login-text-muted: #6f8b7d;
  --login-primary: #55d891;
  --login-primary-strong: #7df0b5;
  --login-info: #47c7ff;
  --login-warning: #f5a623;
  --login-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
  --login-radius: 10px;
  --login-font-mono: 'SF Mono', 'Cascadia Code', 'JetBrains Mono', Consolas, monospace;

  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px 20px 40px;
  color: var(--login-text-primary);
  background:
    linear-gradient(rgba(85, 216, 145, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(85, 216, 145, 0.03) 1px, transparent 1px),
    radial-gradient(ellipse 80% 60% at 18% 28%, rgba(85, 216, 145, 0.08), transparent 55%),
    radial-gradient(ellipse 55% 45% at 88% 78%, rgba(71, 199, 255, 0.05), transparent 50%),
    linear-gradient(120deg, #050806 0%, #07100d 50%, #0a1411 100%);
  background-size: 48px 48px, 48px 48px, auto, auto, auto;
}

.shell {
  width: min(1180px, 100%);
  display: grid;
  grid-template-columns: 1.2fr 0.9fr;
  border: 1px solid var(--login-border-strong);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(8, 15, 12, 0.72);
  box-shadow: var(--login-shadow);
  backdrop-filter: blur(10px);
}

.brand-pane {
  min-width: 0;
  padding: 36px 32px 28px;
  border-right: 1px solid var(--login-border);
  background:
    linear-gradient(160deg, rgba(16, 41, 30, 0.5), transparent 58%),
    linear-gradient(180deg, rgba(13, 23, 19, 0.35), rgba(5, 8, 6, 0.18));
  display: flex;
  flex-direction: column;
  gap: 22px;
  min-height: 680px;
}

.brand-kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--login-primary-strong);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.brand-mark {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(85, 216, 145, 0.4);
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: #10291e;
  color: var(--login-primary-strong);
}

.brand-title {
  margin: 0;
  font-size: 34px;
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.brand-copy {
  margin: 10px 0 0;
  max-width: 460px;
  color: var(--login-text-secondary);
  font-size: 14.5px;
  line-height: 1.65;
}

.ops-board {
  position: relative;
  flex: 1;
  min-height: 320px;
  border: 1px solid var(--login-border);
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(13, 23, 19, 0.96), rgba(7, 14, 11, 0.94)),
    linear-gradient(rgba(85, 216, 145, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(85, 216, 145, 0.04) 1px, transparent 1px);
  background-size: auto, 28px 28px, 28px 28px;
  overflow: hidden;
}

.ops-board-header {
  height: 44px;
  padding: 0 16px;
  border-bottom: 1px solid var(--login-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(17, 29, 24, 0.82);
}

.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--login-text-primary);
  font-size: 13px;
  font-weight: 700;
}

.board-note {
  color: var(--login-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.topology-wrap {
  position: absolute;
  inset: 44px 0 0;
}

.topology {
  width: 100%;
  height: 100%;
  display: block;
}

.topology-line {
  fill: none;
  stroke: rgba(85, 216, 145, 0.38);
  stroke-width: 1.4;
  stroke-dasharray: 6 8;
  animation: lineFlow 8s linear infinite;
}

.topology-line.is-blue {
  stroke: rgba(71, 199, 255, 0.4);
  animation-duration: 9.5s;
}

.topology-line.is-warning {
  stroke: rgba(245, 166, 35, 0.4);
  animation-duration: 10.5s;
}

.node {
  position: absolute;
  min-width: 118px;
  padding: 10px 12px;
  border: 1px solid var(--login-border-strong);
  border-radius: var(--login-radius);
  background: rgba(9, 18, 14, 0.95);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.node-core {
  top: 46%;
  left: 50%;
  min-width: 148px;
  border-color: rgba(85, 216, 145, 0.58);
  transform: translate(-50%, -50%);
}

.node-prometheus {
  top: 14%;
  left: 10%;
}

.node-alert {
  top: 14%;
  right: 10%;
  border-color: rgba(245, 166, 35, 0.42);
}

.node-k8s {
  bottom: 12%;
  left: 14%;
  border-color: rgba(71, 199, 255, 0.42);
}

.node-docker {
  right: 12%;
  bottom: 12%;
}

.node-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--login-text-primary);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.node-meta {
  margin-top: 5px;
  color: var(--login-text-muted);
  font-family: var(--login-font-mono);
  font-size: 11px;
  white-space: nowrap;
}

.node-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--login-primary-strong);
  font-family: var(--login-font-mono);
  font-size: 11px;

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: currentColor;
  }
}

.node-badge.is-info {
  color: #a7e8ff;
}

.node-badge.is-warning {
  color: #ffd78d;
}

.capability-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.capability {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--login-border);
  border-radius: var(--login-radius);
  background: rgba(8, 17, 13, 0.72);
  color: var(--login-text-secondary);
  font-size: 12.5px;
}

.capability-icon {
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  border-radius: 7px;
  border: 1px solid rgba(85, 216, 145, 0.22);
  background: rgba(85, 216, 145, 0.08);
  color: var(--login-primary-strong);
  display: grid;
  place-items: center;
}

.brand-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--login-text-muted);
  font-size: 12px;
}

.env-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px;
  border: 1px solid rgba(71, 199, 255, 0.28);
  border-radius: 999px;
  background: rgba(71, 199, 255, 0.08);
  color: #bceeff;
  font-family: var(--login-font-mono);
  font-size: 11px;
  white-space: nowrap;

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--login-info);
    opacity: 0.9;
  }
}

.login-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--login-surface);
  min-height: 680px;
}

.login-head {
  padding: 28px 32px 20px;
  border-bottom: 1px solid var(--login-border);
  background:
    linear-gradient(90deg, rgba(85, 216, 145, 0.1), transparent 70%),
    #101c17;
}

.login-secure {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--login-primary-strong);
  font-size: 12px;
  font-weight: 700;
}

.login-title {
  margin: 10px 0 0;
  color: var(--login-text-primary);
  font-size: 26px;
  line-height: 1.2;
  font-weight: 800;
}

.login-copy {
  margin: 8px 0 0;
  color: var(--login-text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.login-form {
  flex: 1;
  padding: 28px 32px 20px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.login-form :deep(.el-form-item) {
  margin: 0;
  display: grid;
  gap: 7px;
}

.login-form :deep(.el-form-item__label) {
  height: auto;
  margin: 0;
  padding: 0;
  justify-content: flex-start;
  color: var(--login-text-secondary);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
}

.login-form :deep(.el-form-item__content) {
  line-height: 1;
}

.login-form :deep(.el-form-item__error) {
  position: static;
  margin-top: 4px;
  color: #ff8c90;
  line-height: 1.35;
}

.login-form :deep(.el-input__wrapper) {
  height: 44px;
  border: 1px solid var(--login-border);
  border-radius: var(--login-radius);
  background: var(--login-surface-muted);
  box-shadow: none;
  transition: border-color 180ms ease-out, background 180ms ease-out, box-shadow 180ms ease-out;

  &:hover {
    border-color: #315d4b;
    background: var(--login-surface-strong);
  }

  &.is-focus {
    border-color: var(--login-primary);
    background: var(--login-surface-strong);
    box-shadow: 0 0 0 3px rgba(85, 216, 145, 0.16);
  }
}

.login-form :deep(.el-input__inner) {
  color: var(--login-text-primary);
  font-size: 14px;

  &::placeholder {
    color: #81998d;
  }
}

.login-form :deep(.el-input__prefix .el-icon),
.login-form :deep(.el-input__password .el-icon) {
  color: var(--login-text-muted);
}

.captcha-row {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 118px;
  gap: 10px;
  align-items: start;
}

.captcha-button {
  width: 118px;
  height: 44px;
  padding: 0;
  border: 1px solid rgba(71, 199, 255, 0.35);
  border-radius: var(--login-radius);
  background:
    linear-gradient(90deg, rgba(71, 199, 255, 0.1), rgba(85, 216, 145, 0.08)),
    #e9f7f2;
  color: #0d7163;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 180ms ease-out, transform 180ms ease-out;

  &:hover,
  &:focus-visible {
    border-color: var(--login-info);
    outline: none;
    transform: translateY(-1px);
  }

  &:disabled {
    cursor: wait;
    opacity: 0.8;
    transform: none;
  }
}

.captcha-img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.captcha-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: #0d7163;
  font-family: var(--login-font-mono);
  font-size: 13px;
  font-weight: 800;
}

.login-button {
  width: 100%;
  height: 46px;
  margin-top: 8px;
  border: 1px solid rgba(125, 240, 181, 0.55);
  border-radius: var(--login-radius);
  background: var(--login-primary);
  color: #052216;
  font-weight: 800;
  transition: background 180ms ease-out, transform 180ms ease-out, box-shadow 180ms ease-out;

  &:hover {
    border-color: rgba(125, 240, 181, 0.72);
    background: var(--login-primary-strong);
    color: #052216;
    box-shadow: 0 4px 12px rgba(85, 216, 145, 0.18);
    transform: translateY(-1px);
  }

  &:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(85, 216, 145, 0.22);
  }

  &:active {
    transform: translateY(0);
  }
}

.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--login-text-muted);
  font-size: 12px;
}

.login-panel-bottom {
  margin-top: auto;
  padding: 14px 32px;
  border-top: 1px solid var(--login-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(8, 17, 13, 0.72);
  color: var(--login-text-muted);
  font-size: 12px;
}

.icon {
  width: 15px;
  height: 15px;
  display: inline-block;
  flex: 0 0 auto;

  svg {
    width: 100%;
    height: 100%;
    display: block;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
}

@keyframes lineFlow {
  to {
    stroke-dashoffset: -90;
  }
}

@media (prefers-reduced-motion: reduce) {
  .topology-line {
    animation: none;
    stroke-dasharray: none;
  }

  .captcha-button,
  .login-button,
  .login-form :deep(.el-input__wrapper) {
    transition: none;
  }
}

@media (max-width: 980px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .brand-pane {
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--login-border);
    padding: 28px 24px 22px;
    gap: 16px;
  }

  .brand-title {
    font-size: 28px;
  }

  .ops-board {
    min-height: 280px;
  }

  .capability-row {
    grid-template-columns: 1fr 1fr;
  }

  .login-pane {
    min-height: auto;
  }

  .login-head,
  .login-form,
  .login-panel-bottom {
    padding-left: 24px;
    padding-right: 24px;
  }
}

@media (max-width: 560px) {
  .login-page {
    padding: 20px 12px 24px;
  }

  .capability-row {
    grid-template-columns: 1fr;
  }

  .brand-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .captcha-row {
    grid-template-columns: minmax(0, 1fr) 100px;
  }

  .captcha-button {
    width: 100px;
  }

  .node {
    min-width: 104px;
    padding: 8px 10px;
  }

  .node-title {
    font-size: 12px;
  }

  .node-meta {
    font-size: 10px;
  }
}
</style>
