<template>
  <main class="login-page">
    <div class="shell-grid">
      <section class="login-panel" aria-labelledby="login-title">
        <div class="login-panel-top">
          <div class="login-secure">
            <span class="icon" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d="M12 3 5 6v6c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.8 7-9V6z" />
                <path d="m9 12 2 2 4-4" />
              </svg>
            </span>
            SECURITY GATEWAY
          </div>
          <h2 id="login-title" class="login-title">安全登录</h2>
          <p class="login-copy">登录后继续处理监控、告警、终端与发布任务。</p>
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
              v-model="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              size="large"
              autocomplete="username"
              aria-label="账号"
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
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item prop="captcha_code" label="验证码">
            <div class="captcha-row">
              <el-input
                v-model="form.captcha_code"
                placeholder="请输入验证码"
                :prefix-icon="Key"
                size="large"
                inputmode="numeric"
                aria-label="验证码"
                @keyup.enter="handleLogin"
              />
              <button
                class="captcha-button"
                type="button"
                aria-label="刷新验证码"
                title="点击刷新验证码"
                @click="refreshCaptcha"
              >
                <img
                  v-if="captchaUrl"
                  :src="captchaUrl"
                  alt="验证码"
                  class="captcha-img"
                />
                <span v-else class="captcha-placeholder">加载中</span>
              </button>
            </div>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-button"
            aria-label="登录"
            @click="handleLogin"
          >
            <span v-if="!loading">登录</span>
            <span v-else>登录中...</span>
          </el-button>

          <div class="session-row" aria-label="登录安全信息">
            <span>会话有效期 <strong>12h</strong></span>
            <span>RBAC enabled</span>
          </div>
        </el-form>

        <div class="login-panel-bottom">
          <span>Ops Platform</span>
          <span class="health-pill">0 incidents</span>
        </div>
      </section>

      <section class="ops-stage" aria-labelledby="brand-title">
        <div class="status-strip" aria-label="系统入口状态">
          <div class="status-left">
            <span class="live-dot" aria-hidden="true"></span>
            <span class="status-label">生产环境入口</span>
            <span class="status-code">CN-SH / UTC+8</span>
          </div>
          <div class="status-right">
            <span class="status-label">Auth Gateway</span>
            <span class="status-code">HEALTHY</span>
          </div>
        </div>

        <div class="brand-block">
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
            OPS COMMAND CENTER
          </div>
          <h1 id="brand-title" class="brand-title">运维管理平台</h1>
          <p class="brand-copy">
            统一接入主机监控、告警响应、容器发现、批量执行、巡检任务与应用发布，让值班人员从登录开始进入同一张态势图。
          </p>
        </div>

        <div class="ops-board" aria-label="运维态势预览">
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
              实时运维拓扑
            </div>
            <div class="board-tools" aria-hidden="true">
              <span class="tool-dot is-green"></span>
              <span class="tool-dot is-blue"></span>
              <span class="tool-dot is-amber"></span>
            </div>
          </div>

          <div class="topology-wrap">
            <svg class="topology" viewBox="0 0 850 360" preserveAspectRatio="none" aria-hidden="true">
              <path class="topology-line" d="M172 86 C260 70 315 130 410 150" />
              <path class="topology-line is-warning" d="M676 90 C598 76 520 126 430 150" />
              <path class="topology-line is-blue" d="M220 275 C285 230 340 205 420 164" />
              <path class="topology-line" d="M655 276 C590 230 520 202 430 164" />
              <path class="topology-line is-blue" d="M425 164 C425 205 425 232 425 282" />
            </svg>

            <div class="node node-core">
              <div class="node-title">
                Ops Core
                <span class="node-badge">ACTIVE</span>
              </div>
              <div class="node-meta">api/v1 · rbac · audit</div>
            </div>

            <div class="node node-prometheus">
              <div class="node-title">
                Prometheus
                <span class="node-badge">24ms</span>
              </div>
              <div class="node-meta">host metrics · node_exporter</div>
            </div>

            <div class="node node-alert">
              <div class="node-title">
                Alertmanager
                <span class="node-badge is-warning">6</span>
              </div>
              <div class="node-meta">webhook · rules cache</div>
            </div>

            <div class="node node-k8s">
              <div class="node-title">
                K8s Cluster
                <span class="node-badge">SYNC</span>
              </div>
              <div class="node-meta">pods · services · ingress</div>
            </div>

            <div class="node node-docker">
              <div class="node-title">
                Docker Agent
                <span class="node-badge">PULL</span>
              </div>
              <div class="node-meta">start · stop · restart</div>
            </div>
          </div>

          <div class="metrics-rail" aria-label="关键运行指标">
            <div class="metric">
              <div class="metric-label">在线资产</div>
              <div class="metric-value">128</div>
            </div>
            <div class="metric">
              <div class="metric-label">活跃告警</div>
              <div class="metric-value is-warning">06</div>
            </div>
            <div class="metric">
              <div class="metric-label">容器实例</div>
              <div class="metric-value is-info">342</div>
            </div>
            <div class="metric">
              <div class="metric-label">巡检通过率</div>
              <div class="metric-value">98%</div>
            </div>
          </div>
        </div>

        <div class="ops-footer">
          <div class="event-feed">
            <div class="panel-head">
              <span>事件流</span>
              <span>LIVE</span>
            </div>
            <div class="feed-lines" aria-label="近期事件">
              <div class="feed-line">
                <span>10:42</span>
                <span>prod-node-08 CPU 恢复到安全阈值</span>
                <span class="feed-ok">OK</span>
              </div>
              <div class="feed-line">
                <span>10:39</span>
                <span>payment-api 发布审批完成</span>
                <span class="feed-ok">PASS</span>
              </div>
              <div class="feed-line">
                <span>10:35</span>
                <span>k8s-east ingress latency p95 偏高</span>
                <span class="feed-warn">WARN</span>
              </div>
            </div>
          </div>

          <div class="capability-list">
            <div class="panel-head">
              <span>值班能力</span>
              <span>READY</span>
            </div>
            <div class="capabilities">
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
                实时监控告警
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
                资产容器管理
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
                工单协作流转
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
                SSH 批量执行
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/modules/auth'
import { getCaptcha } from '@/api/auth'
import { User, Lock, Key } from '@element-plus/icons-vue'
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
  username: [{ required: true, message: '用户名不能为空', trigger: 'blur' }],
  password: [{ required: true, message: '密码不能为空', trigger: 'blur' }],
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
  --login-bg: #050806;
  --login-surface: #0d1713;
  --login-surface-strong: #111d18;
  --login-surface-muted: #101812;
  --login-border: #1c3028;
  --login-border-strong: #2f5a49;
  --login-text-primary: #f2fff8;
  --login-text-secondary: #a9c4b8;
  --login-text-muted: #6f8b7d;
  --login-primary: #55d891;
  --login-primary-strong: #7df0b5;
  --login-info: #47c7ff;
  --login-warning: #f5a623;
  --login-shadow: 0 2px 8px rgba(0, 0, 0, 0.24);
  --login-radius: 8px;
  --login-font-mono: 'SF Mono', 'Cascadia Code', 'JetBrains Mono', Consolas, monospace;

  position: relative;
  min-height: 100vh;
  color: var(--login-text-primary);
  background:
    linear-gradient(rgba(85, 216, 145, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(85, 216, 145, 0.045) 1px, transparent 1px),
    linear-gradient(115deg, #050806 0%, #07100d 48%, #0a1411 100%);
  background-size: 44px 44px, 44px 44px, auto;
  isolation: isolate;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: -2;
    background:
      linear-gradient(90deg, rgba(71, 199, 255, 0.08), transparent 28%, transparent 72%, rgba(85, 216, 145, 0.08)),
      linear-gradient(180deg, transparent 0%, rgba(5, 8, 6, 0.72) 100%);
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    z-index: -1;
    background: repeating-linear-gradient(
      180deg,
      rgba(242, 255, 248, 0.025) 0,
      rgba(242, 255, 248, 0.025) 1px,
      transparent 1px,
      transparent 4px
    );
    opacity: 0.36;
    pointer-events: none;
  }
}

.shell-grid {
  width: min(1480px, 100%);
  min-height: 100vh;
  margin: 0 auto;
  padding: 32px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 36px;
  align-items: center;
}

.ops-stage {
  min-width: 0;
  display: grid;
  grid-column: 1;
  grid-row: 1;
  gap: 20px;
  align-content: center;
}

.status-strip {
  width: min(760px, 100%);
  padding: 10px 12px;
  border: 1px solid var(--login-border);
  border-radius: var(--login-radius);
  background: rgba(8, 17, 13, 0.84);
  box-shadow: var(--login-shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.status-left,
.status-right {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--login-primary);
  box-shadow: 0 0 0 4px rgba(85, 216, 145, 0.12);
  animation: dotPulse 1.8s ease-out infinite;
  flex: 0 0 auto;
}

.status-label {
  color: var(--login-text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.status-code {
  padding: 3px 8px;
  border: 1px solid rgba(71, 199, 255, 0.32);
  border-radius: 999px;
  background: rgba(71, 199, 255, 0.08);
  color: #bceeff;
  font-family: var(--login-font-mono);
  font-size: 12px;
  white-space: nowrap;
}

.brand-block {
  max-width: 760px;
}

.brand-kicker {
  margin-bottom: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--login-primary-strong);
  font-size: 13px;
  font-weight: 700;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border: 1px solid rgba(85, 216, 145, 0.38);
  border-radius: 7px;
  display: inline-grid;
  place-items: center;
  background: #10291e;
  color: var(--login-primary-strong);
}

.brand-title {
  max-width: 680px;
  margin: 0;
  color: var(--login-text-primary);
  font-size: 48px;
  line-height: 1.12;
  font-weight: 800;
  letter-spacing: 0;
  text-wrap: balance;
}

.brand-copy {
  max-width: 620px;
  margin: 16px 0 0;
  color: var(--login-text-secondary);
  font-size: 16px;
}

.ops-board {
  position: relative;
  width: min(850px, 100%);
  min-height: 410px;
  border: 1px solid var(--login-border);
  border-radius: var(--login-radius);
  background:
    linear-gradient(135deg, rgba(13, 23, 19, 0.96), rgba(7, 14, 11, 0.94)),
    linear-gradient(rgba(85, 216, 145, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(85, 216, 145, 0.05) 1px, transparent 1px);
  background-size: auto, 28px 28px, 28px 28px;
  box-shadow: var(--login-shadow);
  overflow: hidden;
}

.ops-board-header {
  height: 48px;
  padding: 0 18px;
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
  gap: 10px;
  color: var(--login-text-primary);
  font-size: 14px;
  font-weight: 700;
}

.board-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--login-text-muted);
}

.tool-dot.is-green {
  background: var(--login-primary);
}

.tool-dot.is-blue {
  background: var(--login-info);
}

.tool-dot.is-amber {
  background: var(--login-warning);
}

.topology-wrap {
  position: absolute;
  inset: 48px 0 96px;
}

.topology {
  width: 100%;
  height: 100%;
  display: block;
}

.topology-line {
  fill: none;
  stroke: rgba(85, 216, 145, 0.46);
  stroke-width: 1.4;
  stroke-dasharray: 7 8;
  animation: lineFlow 6s linear infinite;
}

.topology-line.is-blue {
  stroke: rgba(71, 199, 255, 0.48);
  animation-duration: 7.5s;
}

.topology-line.is-warning {
  stroke: rgba(245, 166, 35, 0.48);
  animation-duration: 8.5s;
}

.node {
  position: absolute;
  min-width: 126px;
  padding: 10px 12px;
  border: 1px solid var(--login-border-strong);
  border-radius: var(--login-radius);
  background: rgba(9, 18, 14, 0.95);
  box-shadow: var(--login-shadow);

  &::before {
    content: '';
    position: absolute;
    inset: -1px;
    border: 1px solid rgba(85, 216, 145, 0.18);
    border-radius: inherit;
    pointer-events: none;
  }
}

.node-core {
  top: 48%;
  left: 48%;
  min-width: 164px;
  border-color: rgba(85, 216, 145, 0.62);
  transform: translate(-50%, -50%);
}

.node-prometheus {
  top: 16%;
  left: 13%;
}

.node-alert {
  top: 16%;
  right: 10%;
  border-color: rgba(245, 166, 35, 0.5);
}

.node-k8s {
  bottom: 8%;
  left: 18%;
  border-color: rgba(71, 199, 255, 0.48);
}

.node-docker {
  right: 14%;
  bottom: 8%;
}

.node-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--login-text-primary);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.node-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
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

.node-badge.is-warning {
  color: var(--login-warning);
}

.metrics-rail {
  position: absolute;
  right: 18px;
  bottom: 16px;
  left: 18px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(47, 90, 73, 0.72);
  border-radius: var(--login-radius);
  background: rgba(13, 23, 19, 0.88);
}

.metric-label {
  color: var(--login-text-muted);
  font-size: 12px;
}

.metric-value {
  margin-top: 4px;
  color: var(--login-text-primary);
  font-family: var(--login-font-mono);
  font-size: 18px;
  font-weight: 800;
}

.metric-value.is-warning {
  color: #ffd78d;
}

.metric-value.is-info {
  color: #a7e8ff;
}

.ops-footer {
  width: min(850px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 14px;
}

.event-feed,
.capability-list {
  min-width: 0;
  border: 1px solid var(--login-border);
  border-radius: var(--login-radius);
  background: rgba(8, 17, 13, 0.84);
  box-shadow: var(--login-shadow);
  overflow: hidden;
}

.panel-head {
  height: 40px;
  padding: 0 14px;
  border-bottom: 1px solid var(--login-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--login-text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.feed-lines {
  height: 118px;
  padding: 10px 14px;
  display: grid;
  gap: 8px;
  overflow: hidden;
}

.feed-line {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  color: var(--login-text-secondary);
  font-family: var(--login-font-mono);
  font-size: 12px;

  span:nth-child(2) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.feed-ok {
  color: var(--login-primary-strong);
}

.feed-warn {
  color: #ffd78d;
}

.capabilities {
  padding: 12px 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.capability {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--login-text-secondary);
  font-size: 13px;
}

.capability-icon {
  width: 26px;
  height: 26px;
  border: 1px solid rgba(85, 216, 145, 0.24);
  border-radius: 7px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  background: rgba(85, 216, 145, 0.1);
  color: var(--login-primary-strong);
}

.login-panel {
  width: 100%;
  border: 1px solid var(--login-border-strong);
  border-radius: var(--login-radius);
  background: var(--login-surface);
  box-shadow: var(--login-shadow);
  grid-column: 2;
  grid-row: 1;
  overflow: hidden;
}

.login-panel-top {
  min-height: 118px;
  padding: 22px 24px;
  border-bottom: 1px solid var(--login-border);
  display: grid;
  gap: 8px;
  background:
    linear-gradient(90deg, rgba(85, 216, 145, 0.12), transparent 68%),
    #101c17;
}

.login-secure {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--login-primary-strong);
  font-size: 12px;
  font-weight: 700;
}

.login-title {
  margin: 0;
  color: var(--login-text-primary);
  font-size: 26px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0;
}

.login-copy {
  margin: 0;
  color: var(--login-text-secondary);
  font-size: 14px;
}

.login-form {
  padding: 24px;
  display: grid;
  gap: 16px;
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
  grid-template-columns: minmax(0, 1fr) 112px;
  gap: 10px;
  align-items: start;
}

.captcha-button {
  width: 112px;
  height: 44px;
  padding: 0;
  border: 1px solid rgba(71, 199, 255, 0.36);
  border-radius: var(--login-radius);
  background:
    linear-gradient(90deg, rgba(71, 199, 255, 0.08), rgba(85, 216, 145, 0.08)),
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
  border: 1px solid rgba(125, 240, 181, 0.58);
  border-radius: var(--login-radius);
  background: var(--login-primary);
  color: #052216;
  font-weight: 800;
  transition: background 180ms ease-out, transform 180ms ease-out, box-shadow 180ms ease-out;

  &:hover {
    border-color: rgba(125, 240, 181, 0.72);
    background: var(--login-primary-strong);
    color: #052216;
    box-shadow: 0 4px 8px rgba(85, 216, 145, 0.18);
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
  padding-top: 2px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--login-text-muted);
  font-size: 12px;

  strong {
    color: var(--login-text-secondary);
    font-weight: 700;
  }
}

.login-panel-bottom {
  padding: 14px 24px;
  border-top: 1px solid var(--login-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(8, 17, 13, 0.72);
  color: var(--login-text-muted);
  font-size: 12px;
}

.health-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--login-primary-strong);
  font-family: var(--login-font-mono);
  white-space: nowrap;

  &::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--login-primary);
  }
}

.icon {
  width: 18px;
  height: 18px;
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

@keyframes dotPulse {
  0% {
    box-shadow: 0 0 0 0 rgba(85, 216, 145, 0.28);
  }

  70% {
    box-shadow: 0 0 0 8px rgba(85, 216, 145, 0);
  }

  100% {
    box-shadow: 0 0 0 0 rgba(85, 216, 145, 0);
  }
}

@media (max-width: 1180px) {
  .shell-grid {
    grid-template-columns: minmax(0, 1fr) 390px;
    gap: 24px;
    padding: 24px;
  }

  .brand-title {
    font-size: 40px;
  }

  .ops-board {
    min-height: 390px;
  }

  .metrics-rail {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1080px) {
  .login-page {
    overflow-y: auto;
  }

  .shell-grid {
    min-height: auto;
    grid-template-columns: 1fr;
    align-items: start;
  }

  .login-panel {
    grid-column: auto;
    grid-row: auto;
    max-width: 520px;
    margin: 0 auto 24px;
  }

  .ops-stage {
    grid-column: auto;
    grid-row: auto;
    order: 2;
  }

  .brand-title {
    font-size: 34px;
  }

  .ops-footer {
    grid-template-columns: 1fr;
  }
}

@media (max-height: 820px) and (min-width: 941px) {
  .shell-grid {
    gap: 28px;
    padding-top: 20px;
    padding-bottom: 20px;
  }

  .ops-stage {
    gap: 16px;
  }

  .brand-title {
    font-size: 40px;
  }

  .brand-copy {
    margin-top: 10px;
  }

  .ops-board {
    min-height: 386px;
  }

  .ops-footer {
    display: none;
  }

  .login-panel-top {
    min-height: 104px;
    padding-top: 18px;
    padding-bottom: 18px;
  }

  .login-form {
    gap: 13px;
    padding-top: 20px;
    padding-bottom: 20px;
  }
}

@media (max-width: 640px) {
  .shell-grid {
    gap: 18px;
    padding: 16px;
  }

  .status-strip {
    align-items: flex-start;
    flex-direction: column;
  }

  .brand-title {
    font-size: 30px;
  }

  .brand-copy {
    font-size: 15px;
  }

  .ops-board {
    min-height: 560px;
  }

  .topology-wrap {
    inset: 48px 0 160px;
  }

  .node {
    min-width: 118px;
  }

  .node-core {
    top: 45%;
    left: 50%;
  }

  .node-prometheus {
    top: 9%;
    left: 8%;
  }

  .node-alert {
    top: 9%;
    right: 6%;
  }

  .node-k8s {
    bottom: 8%;
    left: 8%;
  }

  .node-docker {
    right: 6%;
    bottom: 8%;
  }

  .metrics-rail {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .capabilities {
    grid-template-columns: 1fr;
  }

  .captcha-row {
    grid-template-columns: 1fr;
  }

  .captcha-button {
    width: 112px;
  }

  .login-panel-top,
  .login-form,
  .login-panel-bottom {
    padding-right: 18px;
    padding-left: 18px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 1ms !important;
  }

  .topology-line {
    stroke-dasharray: none;
  }
}
</style>
