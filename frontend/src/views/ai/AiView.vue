<template>
  <div class="ai-page">
    <!-- 顶部标题栏 -->
    <div class="ai-header">
      <div class="ai-title">
        <el-icon :size="22"><ChatDotRound /></el-icon>
        <h2>AI 助手</h2>
        <el-tag v-if="aiModel" type="info" size="small" effect="plain">{{ aiModel }}</el-tag>
        <el-tag v-else type="warning" size="small" effect="plain">未配置</el-tag>
      </div>
      <el-button text @click="handleClear" :disabled="!messages.length">
        <el-icon><Delete /></el-icon> 清空对话
      </el-button>
    </div>

    <!-- 对话区域 -->
    <div class="ai-chat" ref="chatRef">
      <!-- 欢迎消息 -->
      <div v-if="!messages.length" class="ai-welcome">
        <div class="welcome-icon">
          <el-icon :size="64" color="#409eff"><ChatDotRound /></el-icon>
        </div>
        <h3>你好，我是 AI 助手</h3>
        <p>我可以帮你查询服务器状态、执行巡检、在服务器上执行命令等。也可以随便聊聊。</p>
        <div class="quick-actions">
          <div v-for="q in quickQuestions" :key="q" class="quick-item" @click="handleQuickAsk(q)">
            {{ q }}
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
        <!-- 用户消息 -->
        <template v-if="msg.role === 'user'">
          <div class="msg-body user-body">
            <div class="msg-content user-content">{{ msg.content }}</div>
            <div class="msg-time">{{ msg.time }}</div>
          </div>
          <div class="msg-avatar user-avatar">
            <el-icon :size="18"><User /></el-icon>
          </div>
        </template>

        <!-- 助手消息 -->
        <template v-else>
          <div class="msg-avatar assistant-avatar">
            <el-icon :size="18"><Monitor /></el-icon>
          </div>
          <div class="msg-body assistant-body">
            <!-- 工具执行中 -->
            <div v-if="msg.type === 'tool_start'" class="tool-card tool-running">
              <div class="tool-card-header">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>执行中: {{ toolDisplayName(msg.tool) }}</span>
              </div>
            </div>

            <!-- 工具执行结果（折叠） -->
            <div v-if="msg.type === 'tool_result'" class="tool-card tool-done">
              <details>
                <summary class="tool-card-header tool-card-summary">
                  <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                  <span>{{ toolDisplayName(msg.tool) }} 完成</span>
                  <el-icon class="expand-icon"><ArrowRight /></el-icon>
                </summary>
                <div class="tool-card-body" v-html="renderMarkdown(msg.result || '')" />
              </details>
            </div>

            <!-- 写操作确认 -->
            <div v-if="msg.type === 'tool_confirm'" class="tool-card tool-confirm">
              <div class="tool-card-header">
                <el-icon color="#e6a23c"><WarningFilled /></el-icon>
                <span>需要确认: {{ toolDisplayName(msg.tool) }}</span>
              </div>
              <div class="tool-card-body">
                <pre class="confirm-desc">{{ msg.description }}</pre>
              </div>
              <div class="tool-card-actions">
                <el-button size="small" @click="handleReject(msg)">拒绝</el-button>
                <el-button size="small" type="primary" :loading="confirmLoading" @click="handleConfirm(msg)">
                  确认执行
                </el-button>
              </div>
            </div>

            <!-- 文本消息 -->
            <div v-if="msg.content && msg.type === 'text'" class="msg-content assistant-content markdown-body" v-html="renderMarkdown(msg.content)" />
            <div v-if="msg.type === 'text'" class="msg-time">{{ msg.time }}</div>
          </div>
        </template>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-avatar assistant-avatar">
          <el-icon :size="18"><Monitor /></el-icon>
        </div>
        <div class="msg-body assistant-body">
          <div class="typing-indicator">
            <span /><span /><span />
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="ai-input">
      <div class="input-wrap">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入消息…（Shift+Enter 换行）"
          resize="none"
          @keydown="handleKeydown"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="loading"
          :disabled="!inputText.trim()"
          circle
          @click="handleSend"
        />
      </div>
      <div class="input-tip">
        基于大语言模型，回答仅供参考，请以实际系统数据为准
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import {
  Promotion,
  Delete,
  Loading,
  WarningFilled,
  CircleCheckFilled,
  ChatDotRound,
  User,
  Monitor,
  ArrowRight,
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import {
  sendAiMessageStream,
  confirmAiActionStream,
  rejectAiActionStream,
  getAiInfo,
  type SSEEvent,
} from '@/api/ai'

interface Message {
  role: 'user' | 'assistant'
  content?: string
  time: string
  type?: 'text' | 'tool_start' | 'tool_result' | 'tool_confirm'
  tool?: string
  result?: string
  description?: string
  pending_id?: string
  args?: Record<string, unknown>
}

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const confirmLoading = ref(false)
const chatRef = ref<HTMLElement>()
const conversationId = ref('')
const aiModel = ref('')

const quickQuestions = [
  '今天哪台服务器资源异常？',
  '最近有什么告警？',
  '帮我巡检一下系统',
  '你是什么模型？',
]

// 配置 marked
const renderer = new marked.Renderer()

// 代码块高亮
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  let highlighted: string
  if (lang && hljs.getLanguage(lang)) {
    highlighted = hljs.highlight(text, { language: lang }).value
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  return `<pre><code class="hljs${lang ? ` language-${lang}` : ''}">${highlighted}</code></pre>`
}

marked.setOptions({
  breaks: true,
  gfm: true,
  renderer,
})

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

const TOOL_NAMES: Record<string, string> = {
  query_assets: '查询服务器',
  query_host_metrics: '查询主机指标',
  query_alerts: '查询告警',
  query_containers: '查询容器',
  query_k8s: '查询 K8s 集群',
  query_tickets: '查询工单',
  get_patrol_reports: '查询巡检报告',
  execute_command: '执行命令',
  run_patrol: '执行巡检',
  create_ticket: '创建工单',
}

function toolDisplayName(tool?: string): string {
  return TOOL_NAMES[tool || ''] || tool || '未知工具'
}

function formatArgs(args?: Record<string, unknown>): string {
  if (!args) return ''
  return Object.entries(args)
    .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
    .join('  |  ')
}

function now(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

async function sendMessage(text: string) {
  if (!text.trim() || loading.value) return

  messages.value.push({ role: 'user', content: text, time: now(), type: 'text' })
  scrollToBottom()

  loading.value = true
  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  try {
    for await (const event of sendAiMessageStream(text, conversationId.value || undefined)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '请求失败：' + (e.message || '服务暂时不可用')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function handleSSEEvent(event: SSEEvent, assistantMsg: Message) {
  switch (event.type) {
    case 'text':
      assistantMsg.content = (assistantMsg.content || '') + event.content
      scrollToBottom()
      break

    case 'tool_start':
      messages.value.push({
        role: 'assistant',
        time: now(),
        type: 'tool_start',
        tool: event.tool,
        args: event.args,
      })
      scrollToBottom()
      break

    case 'tool_result': {
      // 移除对应的 tool_start 卡片
      const startIdx = messages.value.findIndex(
        m => m.type === 'tool_start' && m.tool === event.tool,
      )
      if (startIdx !== -1) messages.value.splice(startIdx, 1)
      messages.value.push({
        role: 'assistant',
        time: now(),
        type: 'tool_result',
        tool: event.tool,
        result: event.result,
      })
      scrollToBottom()
      break
    }

    case 'tool_confirm':
      messages.value.push({
        role: 'assistant',
        time: now(),
        type: 'tool_confirm',
        tool: event.tool,
        description: event.description,
        pending_id: event.pending_id,
        args: event.args,
      })
      scrollToBottom()
      break

    case 'error':
      assistantMsg.content = (assistantMsg.content || '') + '\n\n' + event.content
      scrollToBottom()
      break

    case 'done':
      if (event.conversation_id) {
        conversationId.value = event.conversation_id
      }
      break
  }
}

async function handleConfirm(msg: Message) {
  if (!msg.pending_id || !conversationId.value) return

  confirmLoading.value = true
  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  // 移除确认卡片
  const idx = messages.value.indexOf(msg)
  if (idx !== -1) messages.value.splice(idx, 1)

  try {
    for await (const event of confirmAiActionStream(msg.pending_id, conversationId.value)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '操作失败：' + (e.message || '服务暂时不可用')
  } finally {
    confirmLoading.value = false
    scrollToBottom()
  }
}

async function handleReject(msg: Message) {
  if (!msg.pending_id || !conversationId.value) return

  // 移除确认卡片
  const idx = messages.value.indexOf(msg)
  if (idx !== -1) messages.value.splice(idx, 1)

  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  try {
    for await (const event of rejectAiActionStream(msg.pending_id, conversationId.value)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '请求失败：' + (e.message || '服务暂时不可用')
  } finally {
    scrollToBottom()
  }
}

function handleSend() {
  const text = inputText.value.trim()
  inputText.value = ''
  sendMessage(text)
}

function handleQuickAsk(question: string) {
  sendMessage(question)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleClear() {
  messages.value = []
  conversationId.value = ''
}

onMounted(async () => {
  scrollToBottom()
  try {
    const info = await getAiInfo()
    aiModel.value = info.configured ? info.model : ''
  } catch { /* ignore */ }
})
</script>

<style lang="scss" scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  background: #f5f7fa;
}

// ── Header ──
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;

  .ai-title {
    display: flex;
    align-items: center;
    gap: 8px;
    h2 { margin: 0; font-size: 16px; }
  }
}

// ── Chat ──
.ai-chat {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
}

// ── Welcome ──
.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .welcome-icon { margin-bottom: 16px; }
  h3 { font-size: 20px; margin: 0 0 8px; color: #303133; }
  p { color: #909399; margin: 0 0 24px; max-width: 420px; line-height: 1.6; }

  .quick-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    max-width: 500px;
  }

  .quick-item {
    padding: 8px 16px;
    background: #fff;
    border: 1px solid #dcdfe6;
    border-radius: 20px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: #409eff;
      color: #409eff;
    }
  }
}

// ── Messages ──
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  max-width: 860px;

  &.user {
    margin-left: auto;
    flex-direction: row-reverse;
  }
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.user-avatar {
    background: #409eff;
    color: #fff;
  }

  &.assistant-avatar {
    background: #f0f2f5;
    color: #606266;
  }
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 75%;
  min-width: 0;

  &.user-body { align-items: flex-end; }
  &.assistant-body { align-items: flex-start; }
}

.msg-content {
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;

  &.user-content {
    background: #409eff;
    color: #fff;
    border-radius: 12px 12px 2px 12px;
  }

  &.assistant-content {
    background: #fff;
    color: #303133;
    border-radius: 12px 12px 12px 2px;
    border: 1px solid #e4e7ed;
    white-space: pre-wrap;
    font-family: inherit;
  }
}

.msg-time {
  font-size: 11px;
  color: #c0c4cc;
  padding: 0 4px;
}

// ── Markdown in assistant messages ──
.markdown-body {
  :deep(h1), :deep(h2), :deep(h3) {
    margin: 8px 0 4px;
    font-size: 15px;
    font-weight: 600;
    white-space: normal;
  }

  :deep(p) {
    margin: 4px 0;
    white-space: normal;
  }

  :deep(ul), :deep(ol) {
    margin: 4px 0;
    padding-left: 20px;
    white-space: normal;
  }

  :deep(li) {
    margin: 2px 0;
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    white-space: normal;
  }

  :deep(pre) {
    background: #1e1e1e;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;
    white-space: pre;

    code {
      display: block;
      padding: 12px 14px;
      background: none;
      color: #d4d4d4;
      font-size: 13px;
      line-height: 1.5;
      white-space: pre;
    }
  }

  :deep(blockquote) {
    border-left: 3px solid #dcdfe6;
    margin: 8px 0;
    padding: 4px 12px;
    color: #909399;
    white-space: normal;
  }

  :deep(table) {
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 13px;
    white-space: normal;

    th, td {
      border: 1px solid #e4e7ed;
      padding: 6px 10px;
    }

    th {
      background: #f5f7fa;
      font-weight: 600;
    }
  }

  :deep(strong) { font-weight: 600; }

  :deep(hr) {
    border: none;
    border-top: 1px solid #e4e7ed;
    margin: 8px 0;
  }
}

// ── Tool cards ──
.tool-card {
  border-radius: 10px;
  overflow: hidden;
  font-size: 13px;
  max-width: 100%;

  .tool-card-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    font-weight: 500;
  }

  .tool-card-body {
    padding: 10px 12px;

    :deep(pre) {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
      font-size: 12px;
      line-height: 1.5;
    }

    :deep(code) {
      background: rgba(0, 0, 0, 0.06);
      padding: 1px 4px;
      border-radius: 3px;
      font-size: 12px;
    }

    :deep(pre > code) {
      background: none;
      padding: 0;
    }
  }

  .tool-card-args {
    padding: 0 12px 8px;
    code {
      font-size: 12px;
      color: #909399;
    }
  }

  .tool-card-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 8px 12px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }

  &.tool-running {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    .tool-card-header { color: #0369a1; }
  }

  &.tool-done {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    .tool-card-header { color: #15803d; }

    details {
      &[open] {
        .expand-icon { transform: rotate(90deg); }
      }
    }

    .tool-card-summary {
      cursor: pointer;
      user-select: none;
      list-style: none;
      &::-webkit-details-marker { display: none; }

      .expand-icon {
        margin-left: auto;
        font-size: 12px;
        transition: transform 0.2s;
      }
    }
  }

  &.tool-confirm {
    background: #fffbeb;
    border: 1px solid #fcd34d;
    .tool-card-header { color: #92400e; }

    .confirm-desc {
      margin: 0;
      font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
      white-space: pre-wrap;
      word-break: break-all;
      font-size: 12px;
      line-height: 1.5;
      color: #78350f;
    }
  }
}

// ── Typing indicator ──
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;

  span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #c0c4cc;
    animation: dot-bounce 1.4s ease-in-out infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

// ── Input ──
.ai-input {
  padding: 12px 20px 16px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;

  .input-wrap {
    display: flex;
    gap: 8px;
    align-items: flex-end;

    :deep(.el-textarea__inner) {
      border-radius: 20px;
      padding: 8px 16px;
      resize: none;
    }

    .el-button {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
    }
  }

  .input-tip {
    text-align: center;
    font-size: 11px;
    color: #c0c4cc;
    margin-top: 8px;
  }
}
</style>
