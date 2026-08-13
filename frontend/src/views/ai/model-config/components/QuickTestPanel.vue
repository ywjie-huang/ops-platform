<template>
  <aside class="tc-card">
    <div class="tc-head">
      <div class="sec-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        快速测试
      </div>
      <span v-if="result?.ok" class="tc-dot" title="最近一次试聊成功"></span>
      <span class="sec-sub">{{ subtitle }}</span>
    </div>
    <div class="tc-body" ref="messagesRef" aria-live="polite">
      <div v-if="!messages.length && !sending" class="tc-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>边调参边试聊，验证配置效果<br />消息将用当前草稿配置发送</span>
      </div>
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="msg"
        :class="msg.role === 'user' ? 'user' : 'ai'"
      >
        <div class="m-av">
          <svg v-if="msg.role === 'user'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>
        </div>
        <div class="bubble">{{ msg.content }}</div>
      </div>
      <div v-if="sending" class="msg ai">
        <div class="m-av">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>
        </div>
        <div class="bubble thinking">思考中…</div>
      </div>
    </div>
    <div class="tc-mid" v-if="result">
      <div class="qt-result" :class="result.ok ? 'ok' : 'fail'">
        <svg v-if="result.ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        <span class="qt-result-msg">{{ result.msg }}</span>
      </div>
    </div>
    <div class="tc-foot">
      <div class="qt-input">
        <input
          class="f-input"
          :value="modelValue"
          placeholder="输入测试消息，按 Enter 发送…"
          :disabled="sending"
          @input="onInput"
          @keydown.enter.prevent="$emit('send')"
        />
        <button
          class="btn btn-primary"
          type="button"
          :disabled="!modelValue.trim() || sending"
          @click="$emit('send')"
        >
          <svg v-if="!sending" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          <span v-else class="spinner"></span>
          发送
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  modelValue: string
  messages: Array<{ role: string; content: string }>
  sending?: boolean
  result: { ok: boolean; msg: string } | null
  /** 标题旁的副标题，如「DeepSeek 生产 · 草稿」 */
  subtitle?: string
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
      messagesRef.value.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
    }
  },
)
</script>

<style scoped>
.tc-card {
  min-height: 0; background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--radius, 10px); display: flex; flex-direction: column; overflow: hidden;
  position: relative; box-shadow: 0 1px 2px rgba(17, 17, 17, 0.035);
}
.tc-head {
  padding: 13px 14px; border-bottom: 1px solid var(--border-color);
  display: flex; align-items: center; gap: 9px; flex: none;
}
.sec-title { font-size: 13.5px; font-weight: 700; display: flex; align-items: center; gap: 8px; color: var(--text-primary); }
.sec-title svg { width: 15px; height: 15px; color: var(--text-secondary); }
.sec-sub {
  font-size: 12px; color: var(--text-muted); font-weight: 400;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.tc-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success-color); box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.11); flex: none; }

.tc-body {
  flex: 1; min-height: 0; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 9px; background: var(--surface-2, #f6f6f8);
}
.tc-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 9px; color: var(--text-muted); font-size: 12.5px; text-align: center; line-height: 1.6; padding: 24px;
}
.tc-empty svg { width: 34px; height: 34px; opacity: 0.45; }

/* ── 消息气泡 ── */
.msg { display: flex; gap: 8px; align-items: flex-start; }
.msg.user { flex-direction: row-reverse; }
.m-av {
  width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center;
  flex: none; background: #ececf1; color: var(--text-secondary);
}
.m-av svg { width: 13px; height: 13px; }
.msg.user .m-av { background: var(--primary-bg); color: var(--primary-color); }
.msg.ai .m-av { background: rgba(34, 197, 94, 0.11); color: #15803d; }
.bubble {
  padding: 8px 11px; border-radius: 9px; font-size: 12.5px; line-height: 1.55;
  max-width: 82%; word-break: break-word; white-space: pre-wrap;
}
.msg.user .bubble { background: var(--primary-color); color: #fff; border-bottom-right-radius: 3px; }
.msg.ai .bubble { background: var(--surface-color); border: 1px solid var(--border-color); border-bottom-left-radius: 3px; }
.bubble.thinking { color: var(--text-muted); font-style: italic; }

/* ── 结果条 ── */
.tc-mid { padding: 8px 10px 0; flex: none; }
.qt-result {
  font-size: 12px; font-weight: 600; padding: 7px 11px; border-radius: 7px;
  display: flex; align-items: center; gap: 6px;
}
.qt-result svg { width: 13px; height: 13px; flex: none; }
.qt-result.ok { color: #15803d; background: rgba(34, 197, 94, 0.11); border: 1px solid rgba(34, 197, 94, 0.25); }
.qt-result.fail { color: #b42318; background: rgba(229, 72, 77, 0.1); border: 1px solid rgba(229, 72, 77, 0.25); }
.qt-result-msg { overflow-wrap: anywhere; }

/* ── 输入区 ── */
.tc-foot { padding: 10px; border-top: 1px solid var(--border-color); flex: none; }
.qt-input { display: flex; gap: 8px; }
.qt-input .f-input { flex: 1; min-width: 0; }
.f-input {
  padding: 8px 11px; border: 1px solid var(--border-strong, #e2e2e6); border-radius: 7px; font-size: 13px;
  background: var(--surface-color); color: var(--text-primary); font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.f-input:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.12); }
.f-input:disabled { opacity: 0.55; background: var(--surface-2, #f6f6f8); }

.btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 7px;
  font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border-strong, #e2e2e6);
  background: var(--surface-color); color: var(--text-primary); transition: all 0.15s; font-family: inherit;
}
.btn:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-primary { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--primary-hover); }
.btn svg { width: 13px; height: 13px; }
.spinner {
  width: 13px; height: 13px; border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.tc-body::-webkit-scrollbar { width: 8px; }
.tc-body::-webkit-scrollbar-thumb { background: #d8d8dd; border-radius: 5px; border: 2px solid transparent; background-clip: content-box; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
