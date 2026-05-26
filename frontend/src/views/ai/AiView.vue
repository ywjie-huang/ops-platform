<template>
  <div class="ai-page">
    <!-- 顶部标题栏 -->
    <div class="ai-header">
      <div class="ai-title">
        <span class="ai-icon">🤖</span>
        <h2>AI 运维助手</h2>
        <el-tag type="info" size="small" style="margin-left:8px">Beta</el-tag>
      </div>
      <el-button text @click="handleClear">
        <el-icon><Delete /></el-icon> 清空对话
      </el-button>
    </div>

    <!-- 对话区域 -->
    <div class="ai-chat" ref="chatRef">
      <!-- 欢迎消息 -->
      <div v-if="!messages.length" class="ai-welcome">
        <div class="welcome-icon">🤖</div>
        <h3>你好，我是 AI 运维助手</h3>
        <p>我可以帮你查询服务器状态、执行巡检、在服务器上执行命令等，试试问我：</p>
        <div class="quick-actions">
          <div v-for="q in quickQuestions" :key="q" class="quick-item" @click="handleQuickAsk(q)">
            {{ q }}
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
        <div class="msg-avatar">
          <span v-if="msg.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="msg-body">
          <!-- 工具执行状态 -->
          <div v-if="msg.type === 'tool_start'" class="msg-tool-status">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在执行: {{ msg.tool }}</span>
          </div>
          <div v-if="msg.type === 'tool_result'" class="msg-tool-result">
            <div class="tool-result-header">📋 {{ msg.tool }} 执行结果</div>
            <div class="tool-result-content">{{ msg.result }}</div>
          </div>

          <!-- 写操作确认卡片 -->
          <div v-if="msg.type === 'tool_confirm'" class="msg-confirm-card">
            <div class="confirm-header">
              <el-icon><WarningFilled /></el-icon>
              <span>AI 请求执行以下操作</span>
            </div>
            <div class="confirm-body">
              <pre>{{ msg.description }}</pre>
            </div>
            <div class="confirm-actions">
              <el-button size="small" @click="handleReject(msg)">拒绝</el-button>
              <el-button size="small" type="primary" :loading="confirmLoading" @click="handleConfirm(msg)">
                确认执行
              </el-button>
            </div>
          </div>

          <!-- 文本消息 -->
          <div v-if="msg.content" class="msg-content" v-html="renderContent(msg.content)" />
          <div class="msg-time">{{ msg.time }}</div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
          <div class="msg-content loading-dots">
            <span></span><span></span><span></span>
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
          placeholder="问我任何运维问题…（Shift+Enter 换行）"
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
import { Promotion, Delete, Loading, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  sendAiMessageStream,
  confirmAiActionStream,
  rejectAiActionStream,
  type SSEEvent,
} from '@/api/ai'

interface Message {
  role: 'user' | 'assistant' | 'system'
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

const quickQuestions = [
  '今天哪台服务器资源异常？',
  '最近有什么告警？',
  '帮我巡检一下系统',
  'K8s 集群状态怎么样？',
  '帮我在服务器上看看 Docker 容器状态',
]

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

function renderContent(text: string): string {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/\n/g, '<br>')
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
    assistantMsg.content = '⚠️ 请求失败：' + (e.message || '服务暂时不可用')
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
      })
      scrollToBottom()
      break

    case 'tool_result': {
      const startIdx = messages.value.findIndex(
        m => m.type === 'tool_start' && m.tool === event.tool,
      )
      if (startIdx !== -1) {
        messages.value.splice(startIdx, 1)
      }
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
      assistantMsg.content = (assistantMsg.content || '') + '\n\n⚠️ ' + event.content
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

  const idx = messages.value.indexOf(msg)
  if (idx !== -1) messages.value.splice(idx, 1)

  try {
    for await (const event of confirmAiActionStream(msg.pending_id, conversationId.value)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '⚠️ 操作失败：' + (e.message || '服务暂时不可用')
  } finally {
    confirmLoading.value = false
    scrollToBottom()
  }
}

async function handleReject(msg: Message) {
  if (!msg.pending_id || !conversationId.value) return

  const idx = messages.value.indexOf(msg)
  if (idx !== -1) messages.value.splice(idx, 1)

  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  try {
    for await (const event of rejectAiActionStream(msg.pending_id, conversationId.value)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '⚠️ 请求失败：' + (e.message || '服务暂时不可用')
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

onMounted(scrollToBottom)
</script>

<style lang="scss" scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  background: #f5f7fa;
}

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
    .ai-icon { font-size: 24px; }
    h2 { margin: 0; font-size: 16px; }
  }
}

.ai-chat {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .welcome-icon { font-size: 64px; margin-bottom: 16px; }
  h3 { font-size: 20px; margin: 0 0 8px; color: #303133; }
  p { color: var(--text-muted); margin: 0 0 24px; }

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
    border: 1px solid var(--border-color);
    border-radius: 20px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: var(--el-color-primary);
      color: var(--el-color-primary);
      background: rgba(59, 130, 246, 0.05);
    }
  }
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 800px;

  &.user {
    margin-left: auto;
    flex-direction: row-reverse;
    .msg-body { align-items: flex-end; }
    .msg-content {
      background: var(--el-color-primary);
      color: #fff;
      border-radius: 16px 16px 4px 16px;
    }
  }

  &.assistant {
    .msg-content {
      background: #fff;
      color: #303133;
      border-radius: 16px 16px 16px 4px;
      border: 1px solid var(--border-color);
    }
  }
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  background: #f0f2f5;
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 70%;
}

.msg-content {
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 13px;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
  }

  :deep(pre) {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      background: none;
      color: inherit;
      padding: 0;
    }
  }

  :deep(strong) { font-weight: 600; }
}

.msg-time {
  font-size: 11px;
  color: var(--text-muted);
  padding: 0 4px;
}

.msg-tool-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  font-size: 13px;
  color: #0369a1;
}

.msg-tool-result {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  overflow: hidden;

  .tool-result-header {
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    color: #15803d;
    border-bottom: 1px solid #bbf7d0;
  }

  .tool-result-content {
    padding: 10px 12px;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
    color: #374151;
  }
}

.msg-confirm-card {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 12px;
  overflow: hidden;

  .confirm-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    background: #fef3c7;
    font-size: 14px;
    font-weight: 600;
    color: #92400e;
  }

  .confirm-body {
    padding: 12px 14px;

    pre {
      margin: 0;
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
      color: #374151;
      font-family: 'Cascadia Code', 'Fira Code', monospace;
    }
  }

  .confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 10px 14px;
    border-top: 1px solid #fcd34d;
  }
}

.loading-dots {
  display: flex;
  gap: 4px;
  padding: 14px 20px !important;

  span {
    width: 8px;
    height: 8px;
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

.ai-input {
  padding: 12px 20px 16px;
  background: #fff;
  border-top: 1px solid var(--border-color);
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
    color: var(--text-muted);
    margin-top: 8px;
  }
}
</style>
