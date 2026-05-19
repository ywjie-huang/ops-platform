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
        <p>我可以帮你查询服务器状态、告警信息、工单情况等，试试问我：</p>
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
          <div class="msg-content" v-html="renderContent(msg.content)" />
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
import { Promotion, Delete } from '@element-plus/icons-vue'
import { sendAiMessage } from '@/api/ai'

interface Message {
  role: 'user' | 'assistant'
  content: string
  time: string
}

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const chatRef = ref<HTMLElement>()

const quickQuestions = [
  '今天哪台服务器资源异常？',
  '最近有什么告警？',
  'K8s 集群状态怎么样？',
  '工单有多少没处理的？',
  '帮我巡检一下系统',
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
  // 简单 Markdown 渲染
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

async function sendMessage(text: string) {
  if (!text.trim() || loading.value) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: text, time: now() })
  scrollToBottom()

  loading.value = true
  try {
    const res: any = await sendAiMessage({ message: text })
    const reply = res.data?.reply || '抱歉，我暂时无法回答这个问题。'
    messages.value.push({ role: 'assistant', content: reply, time: now() })
  } catch (e: any) {
    messages.value.push({
      role: 'assistant',
      content: '⚠️ 请求失败：' + (e.message || '服务暂时不可用'),
      time: now(),
    })
  } finally {
    loading.value = false
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

// 欢迎页
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

// 消息行
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

  :deep(strong) { font-weight: 600; }
}

.msg-time {
  font-size: 11px;
  color: var(--text-muted);
  padding: 0 4px;
}

// 加载动画
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

// 输入区域
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
