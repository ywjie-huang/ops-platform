<template>
  <div class="ai-page">
    <!-- 左侧栏 -->
    <aside class="ai-sidebar">
      <div class="sidebar-header">
        <el-input
          v-model="searchText"
          placeholder="搜索对话..."
          size="small"
          clearable
          :prefix-icon="Search"
        />
        <el-button type="primary" size="small" @click="handleNewChat">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in filteredConversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: currentConvId === conv.id }"
          @click="handleSelectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
          <el-icon class="conv-delete" @click.stop="handleDeleteConversation(conv.id)">
            <Delete />
          </el-icon>
        </div>
        <div v-if="!filteredConversations.length" class="conv-empty">
          {{ searchText ? '没有匹配的对话' : '暂无对话' }}
        </div>
      </div>
    </aside>

    <!-- 右侧聊天区 -->
    <main class="ai-main">
      <!-- 顶部栏 -->
      <header class="ai-header">
        <div class="header-left">
          <el-icon :size="18"><Monitor /></el-icon>
          <span class="header-title">AI 助手</span>
          <el-tag v-if="aiModel" type="info" size="small" effect="plain">{{ aiModel }}</el-tag>
          <el-tag v-else type="warning" size="small" effect="plain">未配置</el-tag>
        </div>
      </header>

      <!-- 消息区域 -->
      <div class="ai-messages" ref="messagesRef">
        <!-- 欢迎页 -->
        <div v-if="!displayMessages.length" class="ai-welcome">
          <el-icon :size="48" color="#409eff"><ChatDotRound /></el-icon>
          <h3>你好，我是 AI 助手</h3>
          <p>我可以帮你查询服务器状态、执行巡检、在服务器上执行命令等。也可以随便聊聊。</p>
          <div class="quick-actions">
            <div v-for="q in quickQuestions" :key="q" class="quick-item" @click="handleQuickAsk(q)">
              {{ q }}
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-for="(msg, idx) in displayMessages" :key="idx">
          <!-- 用户消息 -->
          <div v-if="msg.type === 'user'" class="msg-row user">
            <div class="msg-meta">
              <div class="msg-avatar user-avatar">U</div>
              <span class="msg-role">你</span>
              <span class="msg-time">{{ msg.time }}</span>
            </div>
            <div class="msg-bubble user-bubble">{{ msg.content }}</div>
          </div>

          <!-- 工具执行中 -->
          <div v-else-if="msg.type === 'tool_start'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
            </div>
            <div class="tool-panel tool-running">
              <div class="tool-header">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span class="tool-name">{{ toolDisplayName(msg.tool) }}</span>
                <span class="tool-args">{{ formatArgs(msg.args) }}</span>
              </div>
            </div>
          </div>

          <!-- 工具结果（折叠） -->
          <div v-else-if="msg.type === 'tool_result'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
            </div>
            <div class="tool-panel tool-done">
              <details>
                <summary class="tool-header">
                  <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                  <span class="tool-name">{{ toolDisplayName(msg.tool) }}</span>
                  <span class="tool-time" v-if="msg.elapsed">{{ msg.elapsed }}ms</span>
                  <el-icon class="expand-icon"><ArrowRight /></el-icon>
                </summary>
                <div class="tool-body">
                  <div v-if="msg.args" class="tool-section">
                    <div class="tool-label">参数:</div>
                    <div class="tool-code">{{ formatArgs(msg.args) }}</div>
                  </div>
                  <div class="tool-section">
                    <div class="tool-label">结果:</div>
                    <div class="tool-code" v-html="renderMarkdown(msg.result || '')" />
                  </div>
                </div>
              </details>
            </div>
          </div>

          <!-- 写操作确认 -->
          <div v-else-if="msg.type === 'tool_confirm'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
            </div>
            <div class="tool-panel tool-confirm">
              <div class="tool-header">
                <el-icon color="#e6a23c"><WarningFilled /></el-icon>
                <span class="tool-name">{{ toolDisplayName(msg.tool) }} — 需要确认</span>
              </div>
              <div class="tool-body">
                <pre class="confirm-desc">{{ msg.description }}</pre>
              </div>
              <div class="tool-actions">
                <el-button size="small" @click="handleReject(msg)">拒绝</el-button>
                <el-button size="small" type="primary" :loading="confirmLoading" @click="handleConfirm(msg)">
                  确认执行
                </el-button>
              </div>
            </div>
          </div>

          <!-- AI 文本回复 -->
          <div v-else-if="msg.type === 'text'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
              <span class="msg-time">{{ msg.time }}</span>
            </div>
            <div class="msg-text markdown-body" v-html="renderMarkdown(msg.content || '')" />
          </div>
        </template>

        <!-- 加载中 -->
        <div v-if="loading" class="msg-row assistant">
          <div class="msg-meta">
            <div class="msg-avatar assistant-avatar">A</div>
            <span class="msg-role assistant-role">AI</span>
          </div>
          <div class="typing-indicator"><span /><span /><span /></div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="ai-input">
        <div class="input-wrap">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入消息... (Shift+Enter 换行)"
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
        <div class="input-tip">基于大语言模型，回答仅供参考</div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import {
  Promotion, Delete, Loading, WarningFilled, CircleCheckFilled,
  ChatDotRound, Monitor, ArrowRight, Search, Plus,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import {
  getAiInfo, getConversations, getMessages, deleteConversation,
  sendAiMessageStream, confirmAiActionStream, rejectAiActionStream,
  type SSEEvent, type Conversation, type ChatMessage,
} from '@/api/ai'

interface DisplayMessage {
  type: 'user' | 'text' | 'tool_start' | 'tool_result' | 'tool_confirm'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  description?: string
  pending_id?: string
  time?: string
  elapsed?: number
}

const searchText = ref('')
const conversations = ref<Conversation[]>([])
const currentConvId = ref<number | null>(null)
const displayMessages = ref<DisplayMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const confirmLoading = ref(false)
const messagesRef = ref<HTMLElement>()
const aiModel = ref('')

const quickQuestions = [
  '今天哪台服务器资源异常？',
  '最近有什么告警？',
  '帮我巡检一下系统',
  '你是什么模型？',
]

const filteredConversations = computed(() => {
  if (!searchText.value) return conversations.value
  const q = searchText.value.toLowerCase()
  return conversations.value.filter(c => c.title.toLowerCase().includes(q))
})

// Markdown 渲染
const renderer = new marked.Renderer()
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  let highlighted: string
  if (lang && hljs.getLanguage(lang)) {
    highlighted = hljs.highlight(text, { language: lang }).value
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  return `<pre><code class="hljs${lang ? ` language-${lang}` : ''}">${highlighted}</code></pre>`
}
marked.setOptions({ breaks: true, gfm: true, renderer })

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

const TOOL_NAMES: Record<string, string> = {
  query_assets: '查询服务器', query_host_metrics: '查询主机指标',
  query_alerts: '查询告警', query_containers: '查询容器',
  query_k8s: '查询 K8s 集群', query_tickets: '查询工单',
  get_patrol_reports: '查询巡检报告', execute_command: '执行命令',
  run_patrol: '执行巡检', create_ticket: '创建工单',
}

function toolDisplayName(tool?: string): string {
  return TOOL_NAMES[tool || ''] || tool || '未知工具'
}

function formatArgs(args?: Record<string, unknown>): string {
  if (!args) return ''
  return Object.entries(args).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('  |  ')
}

function formatTime(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

function now(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

async function loadConversations() {
  try {
    conversations.value = await getConversations()
  } catch { /* ignore */ }
}

async function loadMessages(convId: number) {
  try {
    const msgs = await getMessages(convId)
    displayMessages.value = msgs
      .filter(m => m.role !== 'tool')
      .map(m => {
        if (m.role === 'user') {
          return { type: 'user' as const, content: m.content || '', time: formatTime(m.created_at) }
        }
        return { type: 'text' as const, content: m.content || '', time: formatTime(m.created_at) }
      })
    scrollToBottom()
  } catch { /* ignore */ }
}

function handleNewChat() {
  currentConvId.value = null
  displayMessages.value = []
}

async function handleSelectConversation(id: number) {
  currentConvId.value = id
  await loadMessages(id)
}

async function handleDeleteConversation(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这个对话？', '提示', { type: 'warning' })
    await deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConvId.value === id) {
      currentConvId.value = null
      displayMessages.value = []
    }
  } catch { /* cancelled */ }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  await sendMessage(text)
}

function handleQuickAsk(q: string) {
  sendMessage(q)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

async function sendMessage(text: string) {
  displayMessages.value.push({ type: 'user', content: text, time: now() })
  scrollToBottom()

  loading.value = true
  const textMsg: DisplayMessage = { type: 'text', content: '', time: now() }
  let textMsgPushed = false
  const toolStartTime: Record<string, number> = {}

  try {
    for await (const event of sendAiMessageStream(text, currentConvId.value || undefined)) {
      handleEvent(event, textMsg, () => {
        if (!textMsgPushed) {
          displayMessages.value.push(textMsg)
          textMsgPushed = true
        }
      }, toolStartTime)
    }
    if (!textMsgPushed) {
      displayMessages.value.push(textMsg)
    }
    await loadConversations()
  } catch (e: any) {
    textMsg.content = '请求失败：' + (e.message || '服务暂时不可用')
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function handleEvent(
  event: SSEEvent,
  textMsg: DisplayMessage,
  ensureTextMsg: () => void,
  toolStartTime: Record<string, number>,
) {
  switch (event.type) {
    case 'text':
      ensureTextMsg()
      textMsg.content = (textMsg.content || '') + event.content
      scrollToBottom()
      break
    case 'tool_start':
      toolStartTime[event.tool || ''] = Date.now()
      displayMessages.value.push({ type: 'tool_start', tool: event.tool, args: event.args })
      scrollToBottom()
      break
    case 'tool_result': {
      const startIdx = displayMessages.value.findIndex(
        m => m.type === 'tool_start' && m.tool === event.tool,
      )
      if (startIdx !== -1) displayMessages.value.splice(startIdx, 1)
      const elapsed = toolStartTime[event.tool || '']
        ? Date.now() - toolStartTime[event.tool || '']
        : undefined
      displayMessages.value.push({
        type: 'tool_result', tool: event.tool, result: event.result,
        args: event.args, elapsed,
      })
      scrollToBottom()
      break
    }
    case 'tool_confirm':
      displayMessages.value.push({
        type: 'tool_confirm', tool: event.tool,
        description: event.description, pending_id: event.pending_id,
        args: event.args,
      })
      scrollToBottom()
      break
    case 'error':
      ensureTextMsg()
      textMsg.content = (textMsg.content || '') + '\n\n' + event.content
      scrollToBottom()
      break
    case 'done':
      if (event.conversation_id && !currentConvId.value) {
        currentConvId.value = event.conversation_id
      }
      break
  }
}

async function handleConfirm(msg: DisplayMessage) {
  if (!msg.pending_id || !currentConvId.value) return
  confirmLoading.value = true

  const idx = displayMessages.value.indexOf(msg)
  if (idx !== -1) displayMessages.value.splice(idx, 1)

  const textMsg: DisplayMessage = { type: 'text', content: '', time: now() }
  let textMsgPushed = false
  const toolStartTime: Record<string, number> = {}

  try {
    for await (const event of confirmAiActionStream(msg.pending_id, currentConvId.value)) {
      handleEvent(event, textMsg, () => {
        if (!textMsgPushed) {
          displayMessages.value.push(textMsg)
          textMsgPushed = true
        }
      }, toolStartTime)
    }
    if (!textMsgPushed) displayMessages.value.push(textMsg)
    await loadConversations()
  } catch (e: any) {
    textMsg.content = '操作失败：' + (e.message || '服务暂时不可用')
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } finally {
    confirmLoading.value = false
    scrollToBottom()
  }
}

async function handleReject(msg: DisplayMessage) {
  if (!msg.pending_id || !currentConvId.value) return

  const idx = displayMessages.value.indexOf(msg)
  if (idx !== -1) displayMessages.value.splice(idx, 1)

  const textMsg: DisplayMessage = { type: 'text', content: '', time: now() }
  let textMsgPushed = false
  const toolStartTime: Record<string, number> = {}

  try {
    for await (const event of rejectAiActionStream(msg.pending_id, currentConvId.value)) {
      handleEvent(event, textMsg, () => {
        if (!textMsgPushed) {
          displayMessages.value.push(textMsg)
          textMsgPushed = true
        }
      }, toolStartTime)
    }
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } catch (e: any) {
    textMsg.content = '请求失败：' + (e.message || '服务暂时不可用')
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } finally {
    scrollToBottom()
  }
}

onMounted(async () => {
  scrollToBottom()
  try {
    const info = await getAiInfo()
    aiModel.value = info.configured ? info.model : ''
  } catch { /* ignore */ }
  await loadConversations()
})
</script>

<style lang="scss" scoped>
.ai-page {
  display: flex;
  height: calc(100vh - 56px);
  background: #fff;
}

// ── 左侧栏 ──
.ai-sidebar {
  width: 220px;
  background: #f8f9fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
}

.conv-item {
  padding: 10px 12px;
  border-left: 3px solid transparent;
  cursor: pointer;
  position: relative;
  transition: all 0.15s;

  &:hover {
    background: #ecf5ff;
    .conv-delete { opacity: 1; }
  }

  &.active {
    background: #ecf5ff;
    border-left-color: #409eff;
    .conv-title { color: #303133; font-weight: 500; }
  }
}

.conv-title {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 20px;
}

.conv-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}

.conv-delete {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  color: #909399;
  font-size: 14px;
  transition: opacity 0.15s;
}

.conv-empty {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
}

// ── 右侧主区域 ──
.ai-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ai-header {
  padding: 10px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

// ── 消息区域 ──
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

// ── 欢迎页 ──
.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  h3 { margin: 12px 0 4px; font-size: 18px; color: #303133; }
  p { color: #909399; margin: 0 0 20px; max-width: 400px; line-height: 1.6; font-size: 13px; }
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 460px;
}

.quick-item {
  padding: 8px 16px;
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 20px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  transition: all 0.15s;

  &:hover { border-color: #409eff; color: #409eff; }
}

// ── 消息行 ──
.msg-row {
  margin-bottom: 16px;

  &.user {
    .msg-bubble { margin-left: 28px; }
  }

  &.assistant {
    .msg-text, .tool-panel { margin-left: 28px; }
  }
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.msg-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;

  &.user-avatar { background: #409eff; color: #fff; }
  &.assistant-avatar { background: #67c23a; color: #fff; }
}

.msg-role {
  font-size: 11px;
  color: #409eff;
  &.assistant-role { color: #67c23a; }
}

.msg-time {
  font-size: 10px;
  color: #c0c4cc;
}

// ── 用户消息气泡 ──
.msg-bubble {
  padding: 8px 14px;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;

  &.user-bubble {
    background: #ecf5ff;
    border-left: 3px solid #409eff;
    border-radius: 0 8px 8px 0;
    color: #303133;
  }
}

// ── AI 文本消息 ──
.msg-text {
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}

// ── 工具面板 ──
.tool-panel {
  border-radius: 8px;
  overflow: hidden;
  font-size: 12px;
  max-width: 100%;

  .tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
  }

  .tool-name { font-weight: 500; }
  .tool-args { color: #909399; font-family: monospace; font-size: 11px; }
  .tool-time { color: #c0c4cc; font-size: 10px; margin-left: auto; }

  .tool-body {
    padding: 8px 12px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }

  .tool-section { margin-bottom: 6px; }
  .tool-label { font-size: 10px; color: #909399; margin-bottom: 2px; }
  .tool-code {
    font-family: monospace;
    font-size: 11px;
    color: #606266;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .tool-actions {
    padding: 6px 12px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    display: flex;
    justify-content: flex-end;
    gap: 6px;
  }

  &.tool-running {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    .tool-header { color: #0369a1; }
  }

  &.tool-done {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    .tool-header { color: #15803d; }

    details {
      &[open] .expand-icon { transform: rotate(90deg); }
    }

    summary {
      cursor: pointer;
      list-style: none;
      &::-webkit-details-marker { display: none; }
    }

    .expand-icon {
      margin-left: auto;
      font-size: 12px;
      transition: transform 0.2s;
    }
  }

  &.tool-confirm {
    background: #fdf6ec;
    border: 1px solid #f5dab1;
    .tool-header { color: #92400e; }
  }

  .confirm-desc {
    margin: 0;
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 11px;
    line-height: 1.5;
    color: #78350f;
  }
}

// ── Markdown ──
.markdown-body {
  :deep(h1), :deep(h2), :deep(h3) {
    margin: 8px 0 4px;
    font-size: 15px;
    font-weight: 600;
  }
  :deep(p) { margin: 4px 0; }
  :deep(ul), :deep(ol) { margin: 4px 0; padding-left: 20px; }
  :deep(li) { margin: 2px 0; }
  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 12px;
    font-family: monospace;
  }
  :deep(pre) {
    background: #1e1e1e;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;
    code {
      display: block;
      padding: 12px 14px;
      background: none;
      color: #d4d4d4;
      font-size: 12px;
      line-height: 1.5;
    }
  }
  :deep(blockquote) {
    border-left: 3px solid #dcdfe6;
    margin: 8px 0;
    padding: 4px 12px;
    color: #909399;
  }
  :deep(table) {
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 12px;
    th, td { border: 1px solid #e4e7ed; padding: 6px 10px; }
    th { background: #f5f7fa; font-weight: 600; }
  }
  :deep(strong) { font-weight: 600; }
  :deep(hr) { border: none; border-top: 1px solid #e4e7ed; margin: 8px 0; }
}

// ── 打字指示器 ──
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

// ── 输入区 ──
.ai-input {
  padding: 12px 20px 16px;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.input-wrap {
  display: flex;
  gap: 8px;
  align-items: flex-end;

  :deep(.el-textarea__inner) {
    border-radius: 8px;
    padding: 8px 14px;
    resize: none;
  }

  .el-button {
    flex-shrink: 0;
  }
}

.input-tip {
  font-size: 10px;
  color: #c0c4cc;
  margin-top: 4px;
  text-align: center;
}
</style>
