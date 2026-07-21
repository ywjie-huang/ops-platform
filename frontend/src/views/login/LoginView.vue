<template>
  <main class="login-page">
    <!-- 背景层 -->
    <div class="bg-dots" aria-hidden="true"></div>
    <div class="spotlight" aria-hidden="true"></div>
    <div class="glow-br" aria-hidden="true"></div>
    <span class="meteor m1" aria-hidden="true"></span>
    <span class="meteor m2" aria-hidden="true"></span>
    <span class="meteor m3" aria-hidden="true"></span>
    <span class="meteor m4" aria-hidden="true"></span>

    <!-- 顶栏 -->
    <div class="top-logo">
      <span class="mark" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M4 17l6-5-6-5M12 19h8" /></svg>
      </span>
      Ops Platform
    </div>
    <span class="status-pill">全部服务正常</span>

    <div class="stage">
      <!-- 左侧：品牌 + 拓扑面板 -->
      <section class="brand" aria-labelledby="brand-title">
        <div class="kicker rise d1">INTERNAL OPS CONSOLE</div>
        <h1 id="brand-title" class="title rise d2">运维管理平台</h1>
        <p class="sub rise d3">
          统一处理主机监控、告警事件、容器运维、批量执行与应用发布。登录后进入值班工作台。
        </p>
        <div class="typing rise d4" aria-hidden="true">
          <span class="tw">$ opsctl login --env production</span>
        </div>

        <div class="topology-board rise d5" aria-label="运维拓扑示意">
          <div class="board-head">
            <div class="board-title">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3v18M3 12h18m-14-7 14 14M19 5 5 19" />
              </svg>
              运维拓扑
            </div>
            <div class="board-note">示意接入关系 · 非实时状态</div>
          </div>
          <div class="topology-wrap">
            <svg class="topology" viewBox="0 0 850 320" preserveAspectRatio="none" aria-hidden="true">
              <path class="topology-line l-teal" d="M170 78 C255 64 320 118 420 140" />
              <path class="topology-line l-amber" d="M680 78 C600 64 525 118 430 140" />
              <path class="topology-line l-blue" d="M210 250 C285 210 340 180 420 152" />
              <path class="topology-line l-indigo" d="M650 250 C580 210 520 180 430 152" />
            </svg>
            <div class="node node-core">
              <div class="node-title">Ops Core <span class="node-badge">核心</span></div>
              <div class="node-meta">API · 权限 · 审计</div>
            </div>
            <div class="node node-prometheus">
              <div class="node-title">Prometheus <span class="node-badge">监控</span></div>
              <div class="node-meta">主机指标采集</div>
            </div>
            <div class="node node-alert">
              <div class="node-title">Alertmanager <span class="node-badge is-warning">告警</span></div>
              <div class="node-meta">规则与事件</div>
            </div>
            <div class="node node-k8s">
              <div class="node-title">K8s <span class="node-badge is-info">集群</span></div>
              <div class="node-meta">资源发现</div>
            </div>
            <div class="node node-docker">
              <div class="node-title">Docker Agent <span class="node-badge is-indigo">容器</span></div>
              <div class="node-meta">主机侧代理</div>
            </div>
          </div>
        </div>

        <div class="brand-tags rise d6" aria-label="平台能力">
          <span>监控告警</span><span>资产容器</span><span>批量执行</span><span>工单发布</span>
        </div>
      </section>

      <!-- 右侧：登录卡 -->
      <section class="form-side">
        <div class="auth-card rise d5">
          <div class="card-head">
            <div class="login-secure">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3 5 6v6c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.8 7-9V6zM9 12l2 2 4-4" />
              </svg>
              安全登录
            </div>
            <span class="card-tag">SECURE</span>
          </div>
          <h2 id="login-title" class="sr-only">登录</h2>

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
              <span v-if="!loading">进入工作台</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form>
          <div class="card-note">会话由服务端签发 · 权限由 RBAC 控制</div>
        </div>
        <div class="auth-help rise d6">无法登录？请联系系统管理员</div>
      </section>
    </div>

    <footer class="auth-footer">
      <span>© 2026 OPS PLATFORM</span>
      <span class="sep">·</span>
      <span>内部运维入口</span>
    </footer>
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
  --mono: 'SFMono-Regular', 'Cascadia Code', Consolas, monospace;
  --line: rgba(148, 163, 184, 0.14);
  --t1: #e8edf6;
  --t2: #97a1b3;
  --t3: #5f6b82;
  --acc: #2dd4bf;
  --acc2: #22d3ee;
  --acc-strong: #7ef0dd;

  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 92px 32px 76px;
  overflow: hidden;
  color: var(--t1);
  background: #04070d;
}

/* ── 背景层 ── */
.bg-dots {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(circle, rgba(148, 163, 184, 0.17) 1px, transparent 1px);
  background-size: 26px 26px;
  -webkit-mask-image: radial-gradient(ellipse 78% 68% at 42% 42%, #000 26%, transparent 76%);
  mask-image: radial-gradient(ellipse 78% 68% at 42% 42%, #000 26%, transparent 76%);
}

.spotlight {
  position: absolute;
  top: -190px;
  left: 38%;
  transform: translateX(-50%);
  width: 860px;
  height: 430px;
  border-radius: 50%;
  pointer-events: none;
  background: radial-gradient(ellipse, rgba(45, 212, 191, 0.15), rgba(34, 211, 238, 0.05) 46%, transparent 70%);
  filter: blur(28px);
}

.glow-br {
  position: absolute;
  right: -140px;
  bottom: -160px;
  width: 480px;
  height: 380px;
  border-radius: 50%;
  pointer-events: none;
  background: radial-gradient(ellipse, rgba(129, 140, 248, 0.09), transparent 65%);
  filter: blur(20px);
}

.meteor {
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 999px;
  background: #7ef0dd;
  box-shadow: 0 0 8px 2px rgba(126, 240, 221, 0.35);
  opacity: 0;
  pointer-events: none;

  &::before {
    content: '';
    position: absolute;
    top: 0.5px;
    right: 0;
    width: 90px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(126, 240, 221, 0.7));
  }
}

.meteor.m1 { top: -4%; left: 14%; animation: meteor 9s linear 1s infinite; }
.meteor.m2 { top: -4%; left: 56%; animation: meteor 11s linear 4.5s infinite; }
.meteor.m3 { top: 12%; left: 84%; animation: meteor 10s linear 7s infinite; }
.meteor.m4 { top: -4%; left: 36%; animation: meteor 13s linear 10s infinite; }

@keyframes meteor {
  0% { transform: rotate(215deg) translateX(0); opacity: 1; }
  70% { opacity: 1; }
  100% { transform: rotate(215deg) translateX(-520px); opacity: 0; }
}

/* ── 顶栏 ── */
.top-logo {
  position: absolute;
  top: 24px;
  left: 32px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.top-logo .mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #062a26;
  background: linear-gradient(135deg, var(--acc), var(--acc2));
  box-shadow: 0 4px 14px rgba(45, 212, 191, 0.32);

  svg {
    width: 16px;
    height: 16px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
}

.status-pill {
  position: absolute;
  top: 26px;
  right: 32px;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(10, 14, 22, 0.6);
  color: var(--t2);
  font-size: 12px;
  backdrop-filter: blur(8px);

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--acc);
    box-shadow: 0 0 8px var(--acc);
    animation: dotPulse 2.4s ease-in-out infinite;
  }
}

@keyframes dotPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── 入场逐级上浮 ── */
.rise {
  opacity: 0;
  transform: translateY(16px);
  animation: rise 0.65s cubic-bezier(0.22, 0.8, 0.36, 1) forwards;
}

.d1 { animation-delay: 0.08s; }
.d2 { animation-delay: 0.18s; }
.d3 { animation-delay: 0.28s; }
.d4 { animation-delay: 0.38s; }
.d5 { animation-delay: 0.5s; }
.d6 { animation-delay: 0.62s; }

@keyframes rise {
  to { opacity: 1; transform: none; }
}

/* ── 舞台布局 ── */
.stage {
  position: relative;
  z-index: 1;
  width: min(1180px, 100%);
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  align-items: center;
  gap: 60px;
}

/* ── 左侧品牌面板 ── */
.kicker {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--acc-strong);
}

.title {
  margin: 14px 0 0;
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.15;
  background: linear-gradient(120deg, #fff 25%, var(--acc-strong) 68%, var(--acc2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.sub {
  margin: 12px 0 0;
  max-width: 460px;
  color: var(--t2);
  font-size: 13.5px;
  line-height: 1.7;
}

.typing {
  margin-top: 16px;
  font-family: var(--mono);
  font-size: 12.5px;
  color: var(--acc-strong);
  min-height: 20px;
}

.typing .tw {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  vertical-align: bottom;
  max-width: 0;
  border-right: 2px solid rgba(126, 240, 221, 0.75);
  animation: type 2.4s steps(31) 1s forwards, caret 0.9s step-end infinite;
}

@keyframes type {
  to { max-width: 32ch; }
}

@keyframes caret {
  50% { border-color: transparent; }
}

/* ── 拓扑面板 ── */
.topology-board {
  position: relative;
  margin-top: 24px;
  height: 336px;
  max-width: 560px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 16px;
  overflow: hidden;
  background: linear-gradient(165deg, rgba(13, 19, 30, 0.75), rgba(8, 12, 19, 0.85));
  backdrop-filter: blur(10px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.board-head {
  height: 40px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}

.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;

  svg {
    width: 13px;
    height: 13px;
    fill: none;
    stroke: var(--acc-strong);
    stroke-width: 2;
    stroke-linecap: round;
  }
}

.board-note {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--t3);
  white-space: nowrap;
}

.topology-wrap {
  position: absolute;
  inset: 40px 0 0;

  &::before {
    content: '';
    position: absolute;
    left: 50%;
    top: 46%;
    width: 300px;
    height: 300px;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    pointer-events: none;
    background: radial-gradient(circle, rgba(45, 212, 191, 0.12), transparent 62%);
  }
}

.topology {
  width: 100%;
  height: 100%;
  display: block;
}

.topology-line {
  fill: none;
  stroke-width: 1.3;
  stroke-dasharray: 5 9;
  animation: flow 9s linear infinite;
}

.topology-line.l-teal { stroke: rgba(45, 212, 191, 0.5); }
.topology-line.l-amber { stroke: rgba(251, 191, 36, 0.45); animation-duration: 10.5s; }
.topology-line.l-blue { stroke: rgba(96, 165, 250, 0.5); animation-duration: 8s; }
.topology-line.l-indigo { stroke: rgba(129, 140, 248, 0.5); animation-duration: 11s; }

@keyframes flow {
  to { stroke-dashoffset: -140; }
}

.node {
  position: absolute;
  min-width: 112px;
  padding: 8px 11px;
  border-radius: 10px;
  background: rgba(15, 20, 31, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.16);
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
}

.node-core {
  top: 46%;
  left: 50%;
  min-width: 140px;
  transform: translate(-50%, -50%);
  border-color: rgba(45, 212, 191, 0.55);
  box-shadow: 0 0 22px rgba(45, 212, 191, 0.18), 0 6px 18px rgba(0, 0, 0, 0.35);
}

.node-prometheus { top: 12%; left: 7%; }
.node-alert { top: 12%; right: 7%; border-color: rgba(251, 191, 36, 0.35); }
.node-k8s { bottom: 9%; left: 11%; border-color: rgba(96, 165, 250, 0.35); }
.node-docker { bottom: 9%; right: 9%; border-color: rgba(129, 140, 248, 0.35); }

.node-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 700;
  white-space: nowrap;
}

.node-meta {
  margin-top: 4px;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.05em;
  color: var(--t3);
  white-space: nowrap;
}

.node-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--acc-strong);

  &::before {
    content: '';
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 6px currentColor;
    animation: dotPulse 2.6s ease-in-out infinite;
  }
}

.node-badge.is-warning { color: #fcd34d; }
.node-badge.is-info { color: #93c5fd; }
.node-badge.is-indigo { color: #a5b4fc; }

.brand-tags {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  color: var(--t3);
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.1em;

  span {
    display: inline-flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: rgba(126, 240, 221, 0.5);
    }
  }
}

/* ── 右侧登录卡 ── */
.form-side {
  display: grid;
  justify-items: end;
  min-width: 0;
}

.auth-card {
  width: min(400px, 100%);
  padding: 26px 26px 16px;
  border-radius: 16px;
  background: linear-gradient(170deg, rgba(15, 22, 34, 0.82), rgba(9, 13, 21, 0.88));
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(16px);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.login-secure {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--acc-strong);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;

  svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
}

.card-tag {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--t3);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.login-form {
  display: grid;
  gap: 15px;
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
  color: #dbe2ec;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
}

.login-form :deep(.el-form-item__content) {
  line-height: 1;
}

.login-form :deep(.el-form-item__error) {
  position: static;
  margin-top: 4px;
  color: #fca5a5;
  line-height: 1.35;
}

.login-form :deep(.el-input__wrapper) {
  height: 44px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 10px;
  background: rgba(7, 10, 17, 0.6);
  box-shadow: none;
  transition: border-color 0.14s, box-shadow 0.14s, background 0.14s;

  &:hover {
    border-color: rgba(148, 163, 184, 0.32);
  }

  &.is-focus {
    border-color: rgba(45, 212, 191, 0.65);
    background: rgba(7, 10, 17, 0.85);
    box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.14);
  }
}

.login-form :deep(.el-input__inner) {
  color: var(--t1);
  font-size: 14px;

  &::placeholder {
    color: #475061;
  }
}

.login-form :deep(.el-input__prefix .el-icon),
.login-form :deep(.el-input__suffix .el-icon) {
  color: var(--t3);
}

.captcha-row {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 108px;
  gap: 10px;
  align-items: start;
}

.captcha-button {
  width: 108px;
  height: 44px;
  padding: 0;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 10px;
  background: repeating-linear-gradient(-55deg, #141b2b 0 6px, #0e1424 6px 12px);
  color: var(--acc-strong);
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.14s, transform 0.14s;

  &:hover,
  &:focus-visible {
    border-color: rgba(45, 212, 191, 0.5);
    outline: none;
  }

  &:disabled {
    cursor: wait;
    opacity: 0.8;
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
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 700;
}

.login-button {
  width: 100%;
  height: 46px;
  margin-top: 8px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, #5eead4, #22d3ee);
  color: #04211f;
  font-weight: 800;
  letter-spacing: 0.06em;
  box-shadow: 0 10px 26px rgba(34, 211, 238, 0.24), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  transition: transform 0.15s, filter 0.15s, box-shadow 0.15s;

  &:hover {
    transform: translateY(-1px);
    filter: brightness(1.07);
    box-shadow: 0 14px 30px rgba(34, 211, 238, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  }

  &:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.3);
  }

  &:active {
    transform: translateY(0);
  }
}

.card-note {
  margin-top: 15px;
  text-align: center;
  color: var(--t3);
  font-size: 11px;
}

.auth-help {
  margin-top: 18px;
  width: min(400px, 100%);
  text-align: center;
  color: var(--t2);
  font-size: 12.5px;
}

.auth-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 18px;
  color: var(--t3);
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.03em;
}

.auth-footer .sep {
  opacity: 0.4;
}

@media (prefers-reduced-motion: reduce) {
  .rise {
    animation: none;
    opacity: 1;
    transform: none;
  }

  .typing .tw {
    animation: none;
    max-width: none;
    border-right-color: transparent;
  }

  .meteor {
    display: none;
  }

  .topology-line {
    animation: none;
    stroke-dasharray: none;
  }

  .status-pill::before,
  .node-badge::before {
    animation: none;
  }

  .captcha-button,
  .login-button,
  .login-form :deep(.el-input__wrapper) {
    transition: none;
  }
}

@media (max-width: 1020px) {
  .stage {
    grid-template-columns: 1fr;
    gap: 44px;
  }

  .form-side {
    justify-items: center;
  }

  .sub {
    max-width: none;
  }
}

@media (max-width: 560px) {
  .login-page {
    padding: 88px 18px 70px;
  }

  .title {
    font-size: 31px;
  }

  .topology-board {
    height: 300px;
  }

  .node {
    min-width: 100px;
    padding: 7px 9px;
  }

  .node-meta {
    display: none;
  }

  .auth-card {
    padding: 22px 20px 14px;
  }

  .top-logo {
    left: 20px;
  }

  .status-pill {
    right: 20px;
  }

  .captcha-row {
    grid-template-columns: minmax(0, 1fr) 100px;
  }

  .captcha-button {
    width: 100px;
  }
}
</style>
