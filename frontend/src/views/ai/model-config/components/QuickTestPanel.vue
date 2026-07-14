<template>
  <div class="card">
    <div class="section-title">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      快速测试
    </div>
    <div class="card-content">
      <div class="test-area">
        <div class="test-messages" ref="messagesRef" aria-live="polite">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="test-msg"
            :class="msg.role"
          >
            <div class="test-msg-avatar">
              <svg v-if="msg.role === 'user'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            </div>
            <div class="test-msg-bubble">{{ msg.content }}</div>
          </div>
          <div v-if="sending" class="test-msg assistant">
            <div class="test-msg-avatar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            </div>
            <div class="test-msg-bubble thinking">思考中...</div>
          </div>
        </div>
        <div class="test-input-row">
          <input
            class="form-input"
            :value="modelValue"
            placeholder="输入测试消息，按 Enter 发送..."
            :disabled="sending"
            @input="onInput"
            @keydown.enter.prevent="$emit('send')"
          />
          <button
            class="btn btn-primary"
            :disabled="!modelValue.trim() || sending"
            :class="{ 'is-loading': sending }"
            @click="$emit('send')"
          >
            <svg v-if="!sending" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            <div v-else class="spinner"></div>
            发送
          </button>
        </div>
        <div v-if="result" class="test-result" :class="result.ok ? 'success' : 'error'">
          {{ result.ok ? '✓' : '✗' }} {{ result.msg }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  modelValue: string
  messages: Array<{ role: string; content: string }>
  sending?: boolean
  result: { ok: boolean; msg: string } | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'send'): void
}>()

const messagesRef = ref<HTMLElement | null>(null)

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}

watch(
  () => [props.messages.length, props.sending],
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTo({
        top: messagesRef.value.scrollHeight,
        behavior: 'smooth',
      })
    }
  },
)
</script>

<style scoped>
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title svg { color: var(--text-secondary); }
.card-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 12px;
}
.test-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.test-messages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
  padding: 12px;
  background: var(--bg-color);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}
.test-msg {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.test-msg.user { flex-direction: row-reverse; }
.test-msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f0f0f0;
}
.test-msg.user .test-msg-avatar {
  background: var(--primary-bg);
  color: var(--primary-color);
}
.test-msg.assistant .test-msg-avatar {
  background: #e8f5e9;
  color: #4caf50;
}
.test-msg-bubble {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  max-width: 80%;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.test-msg.user .test-msg-bubble {
  background: var(--primary-color);
  color: white;
  border-bottom-right-radius: 2px;
}
.test-msg.assistant .test-msg-bubble {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 2px;
}
.test-msg-bubble.thinking {
  color: var(--text-muted);
  font-style: italic;
}
.test-input-row {
  display: flex;
  gap: 8px;
}
.test-input-row .form-input { flex: 1; }
.form-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  background: var(--surface-color);
  color: var(--text-primary);
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-primary);
}
.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}
.btn:disabled, .btn.is-loading {
  opacity: 0.5;
  cursor: not-allowed;
}
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.test-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
}
.test-result.success {
  background: var(--success-bg, #f0fdf4);
  color: var(--success-color, #16a34a);
  border: 1px solid var(--success-border, #bbf7d0);
}
.test-result.error {
  background: var(--error-bg, #fef2f2);
  color: var(--error-color, #dc2626);
  border: 1px solid var(--error-border, #fecaca);
}
</style>
