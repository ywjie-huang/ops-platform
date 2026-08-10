<template>
  <div v-if="visible" class="login-overlay">
    <div class="login-card">
      <h2>
        <span class="lk">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 018 0v3"/></svg>
        </span>
        连接到 {{ hostName || hostIp }}
      </h2>
      <div class="sub">{{ loginForm.username || 'root' }}@{{ hostIp }}:{{ loginForm.port }} · SSH-2.0</div>

      <label>认证方式</label>
      <div class="key-picker">
        <div
          class="kopt"
          :class="{ sel: loginForm.authMode === 'asset' }"
          @click="selectAuthMode('asset')"
        >
          <span class="rd" />
          <span class="kn">资产凭据</span>
          <span class="ks">手动输入</span>
        </div>
        <div
          v-for="key in sshKeys"
          :key="key.id"
          class="kopt"
          :class="{ sel: loginForm.authMode === `key-${key.id}` }"
          @click="selectAuthMode(`key-${key.id}`)"
        >
          <span class="rd" />
          <span class="kn">{{ key.name }}</span>
          <span class="ks">{{ key.auth_type === 'key' ? '私钥' : '密码' }} · {{ key.username }}</span>
        </div>
      </div>

      <label>登录用户</label>
      <input
        v-model="loginForm.username"
        class="lfield"
        type="text"
        placeholder="root"
        :disabled="loginForm.authMode !== 'asset'"
        spellcheck="false"
      />

      <template v-if="loginForm.authMode === 'asset'">
        <label>SSH 密码</label>
        <input
          v-model="loginForm.password"
          class="lfield"
          type="password"
          placeholder="请输入 SSH 密码"
          @keyup.enter="handleConnect"
        />
      </template>

      <button type="button" class="lbtn" :disabled="connecting" @click="handleConnect">
        {{ connecting ? '连接中…' : '连 接' }}
      </button>

      <div v-if="lastError" class="lerr">上次连接失败：{{ lastError }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  visible: boolean
  hostIp: string
  hostName?: string
  sshKeys: any[]
  connecting: boolean
  connected: boolean
  lastError?: string | null
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  connect: [formData: { username: string; password: string; port: number; authMode: string }]
}>()

const loginForm = ref({
  username: 'root',
  password: '',
  port: 22,
  authMode: 'asset',
})

function selectAuthMode(mode: string) {
  loginForm.value.authMode = mode
  if (mode === 'asset') return
  const keyId = Number(mode.replace('key-', ''))
  const key = props.sshKeys.find((item) => item.id === keyId)
  if (key) {
    loginForm.value.username = key.username
    loginForm.value.port = key.port
  }
}

function handleConnect() {
  emit('connect', { ...loginForm.value })
}

function setDefaults(username: string, port: number) {
  loginForm.value.username = username
  loginForm.value.port = port
}

function setAuthMode(mode: string) {
  loginForm.value.authMode = mode
}

function clearPassword() {
  loginForm.value.password = ''
}

defineExpose({ setDefaults, setAuthMode, clearPassword, loginForm })
</script>

<style scoped lang="scss">
.login-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(6, 7, 11, 0.66);
  backdrop-filter: blur(6px);
  border-radius: inherit;
}
.login-card {
  width: min(400px, 100%);
  max-height: 100%;
  overflow-y: auto;
  padding: 28px;
  border-radius: 18px;
  background: var(--ssh-card);
  box-shadow:
    inset 0 0 0 1px var(--ssh-line),
    0 30px 80px rgba(0, 0, 0, 0.5),
    0 0 60px var(--ssh-accent-glow);
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: var(--ssh-line-2); border-radius: 3px; }
  h2 {
    display: flex;
    align-items: center;
    gap: 11px;
    font-size: 16px;
    font-weight: 700;
    color: var(--ssh-t1);
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
}
.lk {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  background: linear-gradient(135deg, var(--ssh-accent), var(--ssh-accent-2));
  box-shadow: 0 4px 14px var(--ssh-accent-glow);
  svg { width: 16px; height: 16px; }
}
.sub {
  font-family: var(--ssh-mono);
  font-size: 11px;
  color: var(--ssh-t3);
  margin: 6px 0 20px 45px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ssh-t4);
  margin: 14px 0 7px;
}
.key-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: var(--ssh-line-2); border-radius: 3px; }
}
.kopt {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 13px;
  border-radius: 11px;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px var(--ssh-line);
  color: var(--ssh-t2);
  flex-shrink: 0;
  &:hover { box-shadow: inset 0 0 0 1px var(--ssh-line-2); background: var(--ssh-glass); }
  &.sel { box-shadow: inset 0 0 0 1.5px var(--ssh-accent); background: var(--ssh-accent-bg); color: var(--ssh-t1); }
}
.rd {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid var(--ssh-t4);
  flex-shrink: 0;
}
.kopt.sel .rd {
  border-color: var(--ssh-accent);
  background: radial-gradient(circle, var(--ssh-accent) 42%, transparent 48%);
}
.kn {
  font-size: 12.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ks {
  margin-left: auto;
  font-family: var(--ssh-mono);
  font-size: 10px;
  color: var(--ssh-t3);
  flex-shrink: 0;
}
.lfield {
  width: 100%;
  height: 38px;
  padding: 0 13px;
  border: none;
  border-radius: 10px;
  outline: none;
  font-family: var(--ssh-mono);
  font-size: 12.5px;
  color: var(--ssh-t1);
  background: var(--ssh-term-bg);
  box-shadow: inset 0 0 0 1px var(--ssh-line-2);
  &:focus { box-shadow: inset 0 0 0 1.5px var(--ssh-accent); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
  &::placeholder { color: var(--ssh-t4); }
}
.lbtn {
  width: 100%;
  height: 40px;
  margin-top: 22px;
  border: none;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--ssh-accent), var(--ssh-accent-2));
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 6px 20px var(--ssh-accent-glow);
  &:hover:not(:disabled) { filter: brightness(1.12); }
  &:disabled { opacity: 0.65; cursor: not-allowed; }
}
.lerr {
  margin-top: 14px;
  padding: 9px 12px;
  border-radius: 10px;
  background: var(--ssh-err-bg);
  box-shadow: inset 0 0 0 1px rgba(248, 113, 113, 0.25);
  font-size: 11.5px;
  color: var(--ssh-err);
  font-family: var(--ssh-mono);
  word-break: break-all;
}
</style>
