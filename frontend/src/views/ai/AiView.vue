<template>
  <div class="ai-root">
    <!-- 左：会话列表 -->
    <aside class="ai-sidebar" ref="sidebarRef">
      <div class="cs-head">
        <button class="new-btn" @click="handleNewChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新对话
        </button>
        <div class="cs-search" v-if="conversations.length > 6 || searchText">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input v-model="searchText" placeholder="搜索会话" />
        </div>
      </div>
      <div class="cs-list">
        <template v-for="g in groupedConversations" :key="g.label || 'flat'">
          <div v-if="g.label" class="cs-group">{{ g.label }}</div>
          <div
            v-for="conv in g.items"
            :key="conv.id"
            class="conv"
            :class="{ active: currentConvId === conv.id }"
            @click="handleSelectConversation(conv.id)"
          >
            <div class="conv-text">
              <input
                v-if="renamingId === conv.id"
                v-model="renameText"
                class="conv-rename"
                @click.stop
                @keydown.enter.prevent="commitRename(conv, true)"
                @keydown.esc.prevent="commitRename(conv, false)"
                @blur="commitRename(conv, true)"
              />
              <div v-else class="conv-title">{{ conv.title }}</div>
              <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
            </div>
            <button class="more" title="重命名 / 删除" @click.stop="toggleMenu(conv.id)">⋯</button>
            <div v-if="menuForId === conv.id" class="conv-menu" @click.stop>
              <button @click="startRename(conv)">重命名</button>
              <button class="danger" @click="handleDeleteConversation(conv.id)">删除</button>
            </div>
          </div>
        </template>
        <div v-if="!filteredConversations.length" class="cs-empty">
          {{ searchText ? '没有匹配的会话' : '暂无会话，点击「新对话」开始' }}
        </div>
      </div>
    </aside>
    <!-- 右：聊天区 -->
    <div class="chat">
      <div class="chat-head">
        <span class="chat-title">{{ currentTitle }}</span>
        <span v-if="configured" class="model-chip">
          <img v-if="providerLogo" :src="providerLogo" alt="" />
          {{ aiProfileName || '当前模型' }} · {{ aiModel }}
        </span>
        <span v-else class="model-chip warn">
          未配置模型
          <span class="lnk" @click="goModelConfig">去配置 →</span>
        </span>
        <div class="spacer"></div>
        <span class="head-ghost">会话自动保存</span>
      </div>

      <!-- 未配置引导 -->
      <div v-if="!configured" class="chat-body center-body">
        <div class="uc-card">
          <div class="uc-ic">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <div class="uc-t">还没有配置模型</div>
          <div class="uc-d">智能助手依赖大模型工作。前往「模型配置」添加一个服务商，几分钟即可开始使用。</div>
          <div class="uc-steps">
            <div class="uc-step"><span class="uc-num">1</span>选择服务商（OpenAI / DeepSeek / 智谱 等）</div>
            <div class="uc-step"><span class="uc-num">2</span>填入 API Key，点「测试连接」验证</div>
            <div class="uc-step"><span class="uc-num">3</span>保存并设为「当前使用」，回来即可对话</div>
          </div>
          <button class="btn btn-primary uc-cta" @click="goModelConfig">前往模型配置 →</button>
        </div>
      </div>
      <!-- 欢迎页（新对话） -->
      <div v-else-if="!displayMessages.length" class="chat-body center-body">
        <div class="w-hero">
          <div class="w-ic"><img :src="assistantLogo" alt="AI" /></div>
          <div class="w-title">你好，我是运维智能助手</div>
          <div class="w-sub">
            可以查询主机与告警状态、解读巡检报告、协助排查故障；<br />
            涉及重启、变更等危险操作会先请你确认。
          </div>
          <div class="w-grid">
            <button v-for="q in quickQuestions" :key="q.title" class="w-card" @click="handleQuickAsk(q.ask)">
              <div class="wc-t">{{ q.title }}</div>
              <div class="wc-d">{{ q.desc }}</div>
            </button>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-else class="chat-body" ref="messagesRef" @scroll="onMsgScroll">
        <div class="mcol">
          <template v-for="(msg, idx) in displayMessages" :key="idx">
            <!-- 用户消息 -->
            <div v-if="msg.type === 'user'" class="mrow user">
              <div class="m-av">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </div>
              <div class="m-main">
                <div class="m-meta"><span class="m-name">我</span><span class="m-time">{{ msg.time }}</span></div>
                <div class="bubble">{{ msg.content }}</div>
              </div>
            </div>
            <!-- 思考 / 工具调用 trace -->
            <div v-else-if="msg.type === 'tool_trace'" class="mrow ai">
              <div class="m-av"><img :src="assistantLogo" alt="AI" /></div>
              <div class="m-main wide">
                <div class="m-meta"><span class="m-name">智能助手</span><span class="m-time">{{ msg.time }}</span></div>
                <div class="tool-card">
                  <details :open="traceRunning(msg)">
                    <summary>
                      <svg class="tc-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
                      <span v-if="traceRunning(msg)" class="tc-spin"></span>
                      <span v-else class="tc-ic">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                      </span>
                      <span class="tc-label">{{ traceSummary(msg) }}</span>
                      <span class="tc-elapsed" v-if="traceTotalElapsed(msg)">{{ formatElapsed(traceTotalElapsed(msg)) }}</span>
                    </summary>
                    <div class="tc-steps">
                      <div
                        v-for="(step, i) in msg.steps || []"
                        :key="i"
                        class="tc-step"
                        :class="{ running: step.status === 'running', done: step.status === 'done' }"
                      >
                        <span v-if="step.status === 'running'" class="tc-spin"></span>
                        <span v-else class="tc-num">{{ step.type === 'tool' ? '✓' : i + 1 }}</span>
                        <div class="tc-step-body">
                          <div class="tc-step-name">{{ step.type === 'tool' ? toolDisplayName(step.tool) : traceStepLabel(step) }}</div>
                          <div v-if="step.type === 'note'" class="tc-step-note">{{ step.content }}</div>
                          <div v-else-if="formatArgs(step.args) || step.elapsed" class="tc-step-meta">
                            {{ formatArgs(step.args) }}<template v-if="step.elapsed"> · {{ step.elapsed }}ms</template>
                          </div>
                          <details v-if="step.type === 'tool' && step.result" class="tc-result">
                            <summary>查看结果</summary>
                            <div class="markdown-body" v-html="renderMarkdown(step.result || '')"></div>
                          </details>
                        </div>
                      </div>
                    </div>
                  </details>
                </div>
              </div>
            </div>
            <!-- 写操作确认（含终态） -->
            <div v-else-if="msg.type === 'tool_confirm'" class="mrow ai">
              <div class="m-av"><img :src="assistantLogo" alt="AI" /></div>
              <div class="m-main wide">
                <div class="m-meta"><span class="m-name">智能助手</span><span class="m-time">{{ msg.time }}</span></div>
                <div class="tool-card confirm-card">
                  <div class="cf-head">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    需要确认 · {{ toolDisplayName(msg.tool) }}
                  </div>
                  <div class="cf-body">
                    <pre class="cf-desc">{{ msg.description }}</pre>
                    <div v-if="confirmCommand(msg)" class="cf-cmd">$ {{ confirmCommand(msg) }}</div>
                  </div>
                  <div v-if="!msg.confirmState" class="cf-acts">
                    <button class="btn btn-warn" :disabled="confirmBusy" @click="handleConfirm(msg)">
                      {{ confirmBusy ? '执行中…' : '确认执行' }}
                    </button>
                    <button class="btn" :disabled="confirmBusy" @click="handleReject(msg)">拒绝</button>
                  </div>
                  <div v-else-if="msg.confirmState === 'confirmed'" class="cf-terminal ok">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    已确认执行
                  </div>
                  <div v-else class="cf-terminal no">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    已拒绝，操作未执行
                  </div>
                </div>
              </div>
            </div>
            <!-- AI 文本回复 -->
            <div v-else-if="msg.type === 'text'" class="mrow ai">
              <div class="m-av"><img :src="assistantLogo" alt="AI" /></div>
              <div class="m-main">
                <div class="m-meta"><span class="m-name">智能助手</span><span class="m-time">{{ msg.time }}</span></div>
                <div class="bubble markdown-body" v-html="renderMarkdown(msg.content || '')"></div>
                <div class="m-acts">
                  <button class="act-btn" @click="copyMessage(msg)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    复制
                  </button>
                  <button class="act-btn" :disabled="loading" @click="handleRegenerate(idx)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                    重新生成
                  </button>
                </div>
              </div>
            </div>
          </template>

          <!-- 思考中 -->
          <div v-if="showTyping" class="mrow ai">
            <div class="m-av"><img :src="assistantLogo" alt="AI" /></div>
            <div class="m-main">
              <div class="m-meta"><span class="m-name">智能助手</span></div>
              <div class="bubble"><span class="typing"><i /><i /><i /></span></div>
            </div>
          </div>
        </div>
      </div>
      <button v-show="showNewMsg" class="newmsg-btn" @click="forceScroll">↓ 新消息</button>
      <!-- 输入区 -->
      <div class="chat-input">
        <div class="ci-card">
          <textarea
            ref="inputRef"
            v-model="inputText"
            rows="1"
            :placeholder="configured
              ? '询问主机状态、告警、巡检报告… 也可以让我执行操作（危险操作会先确认）'
              : '请先在「模型配置」中添加并启用模型'"
            :disabled="!configured"
            @keydown="handleKeydown"
            @input="autoGrow"
          ></textarea>
          <div class="ci-bar">
            <span class="ci-hint">Enter 发送 · Shift+Enter 换行</span>
            <div class="spacer"></div>
            <button v-if="!loading" class="ci-send" :disabled="!inputText.trim() || !configured" @click="handleSend">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              发送
            </button>
            <button v-else class="ci-send ci-stop" @click="handleStop">
              <svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
              停止
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, nextTick, onActivated, onBeforeUnmount, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import {
  getAiInfo, getConversations, getMessages, deleteConversation, renameConversation,
  sendAiMessageStream, confirmAiActionStream, rejectAiActionStream,
  type Conversation,
} from '@/api/ai'
import { formatRelativeTime as formatTime } from '@/utils/time'
import {
  applyAiStreamEvent,
  buildDisplayMessagesFromHistory,
  createAiStreamState,
  traceStepLabel,
  traceSummary,
  traceTotalElapsed,
  type AiStreamEvent,
  type AiStreamState,
  type DisplayMessage,
} from './messageDisplay'
import { providerLogoOf } from './providerLogos'
import assistantLogo from '@/assets/ai-assistant.svg'

const router = useRouter()

const searchText = ref('')
const conversations = ref<Conversation[]>([])
const currentConvId = ref<number | null>(null)
const displayMessages = ref<DisplayMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const stopRequested = ref(false)
const confirmBusy = ref(false)
const messagesRef = ref<HTMLElement>()
const sidebarRef = ref<HTMLElement>()
const inputRef = ref<HTMLTextAreaElement>()
const aiModel = ref('')
const aiProvider = ref('')
const aiProfileName = ref('')
const configured = ref(true)
const DEFAULT_CONVERSATION_TITLE = '新对话'
const TITLE_REFRESH_ATTEMPTS = 10
const TITLE_REFRESH_INTERVAL_MS = 600
const quickQuestions = [
  { title: '📊 现在有哪些主机资源异常？', ask: '现在有哪些主机资源异常？', desc: '查询全量主机最新指标' },
  { title: '🚨 最近 24 小时的告警摘要', ask: '给我最近 24 小时的告警摘要', desc: '按严重级别聚合展示' },
  { title: '🔍 帮我排查 CPU 飙高问题', ask: '帮我排查 CPU 飙高的主机', desc: '引导式故障定位' },
  { title: '📝 整理巡检报告交接摘要', ask: '把最新的巡检报告整理成交接摘要', desc: '提炼异常与待办' },
]

const filteredConversations = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  if (!q) return conversations.value
  return conversations.value.filter(c => c.title.toLowerCase().includes(q))
})

function groupLabelOf(dateStr: string): string {
  const t = new Date(dateStr).getTime()
  if (!Number.isFinite(t)) return '更早'
  const nowD = new Date()
  const today = new Date(nowD.getFullYear(), nowD.getMonth(), nowD.getDate()).getTime()
  const DAY = 86400000
  if (t >= today) return '今天'
  if (t >= today - DAY) return '昨天'
  if (t >= today - 7 * DAY) return '7 天内'
  return '更早'
}

const groupedConversations = computed(() => {
  const list = filteredConversations.value
  if (searchText.value.trim()) return [{ label: '', items: list }]
  const order = ['今天', '昨天', '7 天内', '更早']
  const map = new Map<string, Conversation[]>()
  for (const c of list) {
    const label = groupLabelOf(c.updated_at)
    if (!map.has(label)) map.set(label, [])
    map.get(label)!.push(c)
  }
  return order.filter(l => map.has(l)).map(l => ({ label: l, items: map.get(l)! }))
})

const currentTitle = computed(() => {
  if (!currentConvId.value) return '新对话'
  return conversations.value.find(c => c.id === currentConvId.value)?.title || '新对话'
})

const providerLogo = computed(() => providerLogoOf(aiProvider.value))

const showTyping = computed(() => {
  if (!loading.value) return false
  const last = displayMessages.value[displayMessages.value.length - 1]
  return !last || last.type === 'user'
})
// ── Markdown 渲染（AI 输出含用户可控文本，必须 DOMPurify 净化） ──
const renderer = new marked.Renderer()
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  const highlighted = lang && hljs.getLanguage(lang)
    ? hljs.highlight(text, { language: lang }).value
    : hljs.highlightAuto(text).value
  return `<pre><code class="hljs${lang ? ` language-${lang}` : ''}">${highlighted}</code></pre>`
}
marked.setOptions({ breaks: true, gfm: true, renderer })

function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text) as string, {
    USE_PROFILES: { html: true },
  }) as string
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

function formatElapsed(ms?: number): string {
  if (!ms) return ''
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function traceRunning(msg: DisplayMessage): boolean {
  return (msg.steps || []).some(s => s.type === 'tool' && s.status === 'running')
}

function confirmCommand(msg: DisplayMessage): string {
  const cmd = msg.args?.command
  return msg.tool === 'execute_command' && typeof cmd === 'string' ? cmd : ''
}

function now(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
// ── 智能滚动：靠近底部才跟随，否则弹「新消息」浮钮 ──
const stickBottom = ref(true)
const showNewMsg = ref(false)

function onMsgScroll() {
  const el = messagesRef.value
  if (!el) return
  stickBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  if (stickBottom.value) showNewMsg.value = false
}

function maybeScroll() {
  nextTick(() => {
    const el = messagesRef.value
    if (!el) return
    if (stickBottom.value) el.scrollTop = el.scrollHeight
    else showNewMsg.value = true
  })
}

function forceScroll() {
  stickBottom.value = true
  showNewMsg.value = false
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

function autoGrow() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

// ── 会话列表：加载 / 选择 / 新建 / 删除 / 重命名 ──
async function loadConversations() {
  try {
    conversations.value = await getConversations()
  } catch { /* ignore */ }
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitForConversationTitle(conversationId: number) {
  let latest: Conversation[] = []
  for (let attempt = 0; attempt < TITLE_REFRESH_ATTEMPTS; attempt += 1) {
    await delay(TITLE_REFRESH_INTERVAL_MS)
    try {
      latest = await getConversations()
    } catch {
      return
    }
    const conversation = latest.find(c => c.id === conversationId)
    if (conversation && conversation.title !== DEFAULT_CONVERSATION_TITLE) {
      conversations.value = latest
      return
    }
  }
  if (latest.length) conversations.value = latest
}
async function loadMessages(convId: number) {
  try {
    const msgs = await getMessages(convId)
    displayMessages.value = buildDisplayMessagesFromHistory(msgs, formatTime)
    forceScroll()
  } catch { /* ignore */ }
}

function handleNewChat() {
  currentConvId.value = null
  displayMessages.value = []
  nextTick(() => inputRef.value?.focus())
}

async function handleSelectConversation(id: number) {
  if (renamingId.value !== null) return
  currentConvId.value = id
  await loadMessages(id)
}

async function handleDeleteConversation(id: number) {
  menuForId.value = null
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

// ── ⋯ 菜单 ──
const menuForId = ref<number | null>(null)
function toggleMenu(id: number) {
  menuForId.value = menuForId.value === id ? null : id
}
function closeMenu() {
  menuForId.value = null
}

// ── 重命名 ──
const renamingId = ref<number | null>(null)
const renameText = ref('')

function startRename(conv: Conversation) {
  closeMenu()
  renamingId.value = conv.id
  renameText.value = conv.title
  nextTick(() => {
    const el = sidebarRef.value?.querySelector<HTMLInputElement>('.conv-rename')
    el?.focus()
    el?.select()
  })
}

async function commitRename(conv: Conversation, commit: boolean) {
  if (renamingId.value !== conv.id) return
  renamingId.value = null
  const title = renameText.value.trim()
  if (!commit || !title || title === conv.title) return
  try {
    await renameConversation(conv.id, title)
    conv.title = title
  } catch (e: any) {
    ElMessage.error(e.message || '重命名失败')
  }
}
// ── 发送 / 停止 / 重新生成 / 复制 ──
function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  nextTick(autoGrow)
  sendMessage(text)
}

function handleQuickAsk(q: string) {
  sendMessage(q)
}

function handleKeydown(e: Event | KeyboardEvent) {
  if (!(e instanceof KeyboardEvent)) return
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleStop() {
  stopRequested.value = true
}

async function sendMessage(text: string) {
  displayMessages.value.push({ type: 'user', content: text, time: now() })
  forceScroll()

  loading.value = true
  stopRequested.value = false
  const streamState = createAiStreamState()
  let titlePendingConvId: number | null = null
  let stopped = false

  try {
    for await (const event of sendAiMessageStream(text, currentConvId.value || undefined)) {
      if (stopRequested.value) { stopped = true; break }
      handleEvent(event, streamState)
      if (event.title_pending && event.conversation_id) titlePendingConvId = event.conversation_id
    }
    if (stopped) {
      handleEvent({ type: 'done' }, streamState)
      markStopped()
    } else if (titlePendingConvId) {
      await waitForConversationTitle(titlePendingConvId)
    } else {
      await loadConversations()
    }
  } catch (e: any) {
    handleEvent(
      { type: 'error', content: '请求失败：' + (e.message || '服务暂时不可用') },
      streamState,
    )
  } finally {
    loading.value = false
    stopRequested.value = false
  }
}

function markStopped() {
  const last = displayMessages.value[displayMessages.value.length - 1]
  if (last && last.type === 'text') {
    last.content = (last.content || '') + '\n\n*（已停止生成）*'
  }
}

function handleRegenerate(idx: number) {
  if (loading.value) return
  for (let i = idx - 1; i >= 0; i--) {
    const m = displayMessages.value[i]
    if (m.type === 'user' && m.content) {
      sendMessage(m.content)
      return
    }
  }
  ElMessage.info('没有找到可重新生成的提问')
}

async function copyMessage(msg: DisplayMessage) {
  const text = msg.content || ''
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
      ElMessage.success('已复制')
    } catch {
      ElMessage.error('复制失败')
    }
    ta.remove()
  }
}
function handleEvent(event: AiStreamEvent, streamState: AiStreamState) {
  applyAiStreamEvent(event, displayMessages.value, streamState, now)
  if (event.conversation_id && !currentConvId.value) {
    currentConvId.value = event.conversation_id
  }
  maybeScroll()
}

// ── 写操作确认 / 拒绝（保留终态，不再移除卡片） ──
async function handleConfirm(msg: DisplayMessage) {
  if (!msg.pending_id || !currentConvId.value || msg.confirmState || confirmBusy.value) return
  confirmBusy.value = true
  const streamState = createAiStreamState()

  try {
    for await (const event of confirmAiActionStream(msg.pending_id, currentConvId.value)) {
      handleEvent(event, streamState)
    }
    msg.confirmState = 'confirmed'
    await loadConversations()
  } catch (e: any) {
    handleEvent(
      { type: 'error', content: '操作失败：' + (e.message || '服务暂时不可用') },
      streamState,
    )
  } finally {
    confirmBusy.value = false
    maybeScroll()
  }
}

async function handleReject(msg: DisplayMessage) {
  if (!msg.pending_id || !currentConvId.value || msg.confirmState || confirmBusy.value) return
  confirmBusy.value = true
  const streamState = createAiStreamState()

  try {
    for await (const event of rejectAiActionStream(msg.pending_id, currentConvId.value)) {
      handleEvent(event, streamState)
    }
    msg.confirmState = 'rejected'
    await loadConversations()
  } catch (e: any) {
    handleEvent(
      { type: 'error', content: '请求失败：' + (e.message || '服务暂时不可用') },
      streamState,
    )
  } finally {
    confirmBusy.value = false
    maybeScroll()
  }
}

function goModelConfig() {
  router.push('/ai/model')
}

onActivated(async () => {
  window.addEventListener('click', closeMenu)
  forceScroll()
  try {
    const info = await getAiInfo()
    configured.value = info.configured
    aiModel.value = info.configured ? info.model : ''
    aiProvider.value = info.configured ? info.provider || '' : ''
    aiProfileName.value = info.configured ? info.profile_name || '' : ''
  } catch { /* ignore */ }
  await loadConversations()
})
onDeactivated(() => window.removeEventListener('click', closeMenu))
onBeforeUnmount(() => window.removeEventListener('click', closeMenu))
</script>
<style scoped>
.ai-root {
  --surface-2: #f6f6f8;
  --border-strong: #e2e2e6;
  --radius: 10px;
  --success-bg: rgba(34, 197, 94, .11);
  --warning-bg: rgba(245, 166, 35, .13);
  --danger-bg: rgba(229, 72, 77, .1);
  display: flex; min-height: 0; gap: 0;
  height: calc(100vh - var(--header-height) - 40px);
}
.spacer { flex: 1; }
button { font-family: inherit; }

/* ── 左：会话列表 ── */
.ai-sidebar {
  width: 240px; flex: none; display: flex; flex-direction: column; min-height: 0;
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--radius); overflow: hidden;
  box-shadow: 0 1px 2px rgba(17, 17, 17, .035);
}
.cs-head { padding: 12px 12px 8px; display: flex; flex-direction: column; gap: 8px; }
.new-btn {
  width: 100%; display: flex; align-items: center; justify-content: center; gap: 6px;
  background: var(--primary-color); color: #fff; border: 0; border-radius: 8px;
  padding: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background .15s;
}
.new-btn:hover { background: var(--primary-hover); }
.new-btn svg { width: 14px; height: 14px; }
.cs-search { position: relative; }
.cs-search input {
  width: 100%; box-sizing: border-box; padding: 7px 10px 7px 30px;
  border: 1px solid var(--border-strong); border-radius: 7px; font-size: 12.5px;
  background: var(--surface-color); color: var(--text-primary); font-family: inherit;
}
.cs-search input:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94, 106, 210, .12); }
.cs-search svg { position: absolute; left: 9px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: var(--text-muted); }
.cs-list { flex: 1; min-height: 0; overflow-y: auto; padding: 2px 8px 8px; }
.cs-group {
  font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: .05em;
  padding: 10px 8px 4px;
}
.conv {
  display: flex; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 8px;
  cursor: pointer; position: relative; transition: background .12s; border: 1px solid transparent;
}
.conv:hover { background: var(--surface-2); }
.conv.active { background: var(--primary-bg); border-color: rgba(94, 106, 210, .22); }
.conv.active::before {
  content: ''; position: absolute; left: 0; top: 8px; bottom: 8px;
  width: 3px; border-radius: 2px; background: var(--primary-color);
}
.conv-text { flex: 1; min-width: 0; }
.conv-title {
  font-size: 12.5px; font-weight: 600; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.conv-time { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.conv-rename {
  width: 100%; box-sizing: border-box; font-size: 12.5px; font-weight: 600; font-family: inherit;
  border: 1px solid var(--primary-color); border-radius: 5px; padding: 2px 6px;
  color: var(--text-primary); background: var(--surface-color); outline: none;
}
.more {
  display: none; position: absolute; right: 8px; top: 8px;
  border: 1px solid var(--border-strong); background: var(--surface-color); border-radius: 6px;
  width: 22px; height: 22px; color: var(--text-secondary); cursor: pointer; font-size: 14px;
  line-height: 1; place-items: center; padding-bottom: 3px;
}
.conv:hover .more { display: grid; }
.conv-menu {
  position: absolute; right: 8px; top: calc(100% - 2px); z-index: 30; min-width: 88px;
  background: var(--surface-color); border: 1px solid var(--border-strong); border-radius: 8px;
  box-shadow: 0 10px 26px -8px rgba(17, 17, 17, .22); padding: 4px;
  display: flex; flex-direction: column;
}
.conv-menu button {
  border: 0; background: transparent; text-align: left; padding: 6px 10px; border-radius: 5px;
  font-size: 12.5px; color: var(--text-primary); cursor: pointer;
}
.conv-menu button:hover { background: var(--surface-2); }
.conv-menu button.danger { color: #b42318; }
.conv-menu button.danger:hover { background: var(--danger-bg); }
.cs-empty { padding: 24px; text-align: center; font-size: 12.5px; color: var(--text-muted); line-height: 1.6; }
.cs-list::-webkit-scrollbar { width: 8px; }
.cs-list::-webkit-scrollbar-thumb { background: #d8d8dd; border-radius: 5px; border: 2px solid transparent; background-clip: content-box; }
/* ── 右：聊天区骨架 ── */
.chat { flex: 1; min-width: 0; display: flex; flex-direction: column; min-height: 0; position: relative; margin-left: 14px; }
.chat-head {
  flex: none; display: flex; align-items: center; gap: 9px; padding: 10px 16px;
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--radius); box-shadow: 0 1px 2px rgba(17, 17, 17, .035);
}
.chat-title {
  font-size: 13.5px; font-weight: 700; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 40%;
}
.model-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600; color: var(--text-secondary);
  background: var(--surface-2); border: 1px solid var(--border-color);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.model-chip img { width: 13px; height: 13px; object-fit: contain; flex: none; }
.model-chip.warn { color: #b45309; background: var(--warning-bg); border-color: rgba(245, 166, 35, .32); }
.model-chip .lnk { color: var(--primary-color); cursor: pointer; font-weight: 700; }
.head-ghost { font-size: 12px; color: var(--text-muted); }

/* ── 消息区：860px 阅读列宽 ── */
.chat-body {
  flex: 1; min-height: 0; overflow-y: auto; margin-top: 12px;
  padding: 18px 22px 12px;
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--radius); box-shadow: 0 1px 2px rgba(17, 17, 17, .035);
}
.chat-body.center-body { display: flex; align-items: center; justify-content: center; }
.mcol { max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.mrow { display: flex; gap: 9px; align-items: flex-start; animation: fadeUp .18s ease; }
.mrow.user { flex-direction: row-reverse; }
.m-av {
  width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; flex: none;
  background: #ececf1; color: var(--text-secondary); overflow: hidden;
}
.m-av svg { width: 13px; height: 13px; }
.m-av img { width: 18px; height: 18px; object-fit: contain; }
.mrow.user .m-av { background: var(--primary-bg); color: var(--primary-color); }
.mrow.ai .m-av { background: #fff; border: 1px solid var(--border-strong); }
.m-main { min-width: 0; max-width: 82%; display: flex; flex-direction: column; gap: 4px; }
.m-main.wide { max-width: 100%; flex: 1; }
.mrow.user .m-main { align-items: flex-end; }
.m-meta { display: flex; align-items: baseline; gap: 7px; }
.m-name { font-size: 11.5px; font-weight: 600; color: var(--text-secondary); }
.m-time { font-size: 10.5px; color: var(--text-muted); }
.bubble {
  padding: 9px 13px; border-radius: 10px; font-size: 13px; line-height: 1.65;
  word-break: break-word; width: fit-content; max-width: 100%;
}
.mrow.user .bubble { background: var(--primary-color); color: #fff; border-bottom-right-radius: 3px; white-space: pre-wrap; }
.mrow.ai .bubble {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-bottom-left-radius: 3px; box-shadow: 0 1px 2px rgba(17, 17, 17, .03);
}
/* ── AI 消息 hover 操作条 ── */
.m-acts { display: flex; gap: 4px; opacity: 0; transition: opacity .15s; }
.mrow.ai:hover .m-acts { opacity: 1; }
.act-btn {
  display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--border-strong);
  background: var(--surface-color); color: var(--text-secondary); border-radius: 6px;
  padding: 3px 8px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all .13s;
}
.act-btn:hover { border-color: var(--primary-color); color: var(--primary-color); background: var(--primary-bg); }
.act-btn:disabled { opacity: .45; cursor: not-allowed; }
.act-btn svg { width: 11px; height: 11px; }

/* ── 工具执行卡片 ── */
.tool-card {
  background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 9px;
  overflow: hidden; width: 100%; box-shadow: 0 1px 2px rgba(17, 17, 17, .03);
}
.tool-card summary {
  list-style: none; display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; user-select: none;
}
.tool-card summary::-webkit-details-marker { display: none; }
.tool-card summary:hover { background: var(--surface-2); }
.tc-chev { width: 11px; height: 11px; color: var(--text-muted); transition: transform .15s; flex: none; }
details[open] > summary .tc-chev { transform: rotate(90deg); }
.tc-ic { width: 15px; height: 15px; display: grid; place-items: center; flex: none; color: var(--primary-color); }
.tc-ic svg { width: 13px; height: 13px; }
.tc-label { color: var(--text-primary); }
.tc-elapsed { margin-left: auto; font-size: 11px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.tc-steps { border-top: 1px solid var(--border-color); padding: 6px 12px 10px; display: flex; flex-direction: column; }
.tc-step { display: flex; gap: 8px; padding: 5px 0; font-size: 12px; align-items: flex-start; }
.tc-num {
  width: 16px; height: 16px; border-radius: 50%; background: var(--surface-2);
  border: 1px solid var(--border-strong); color: var(--text-secondary);
  font-size: 10px; font-weight: 700; display: grid; place-items: center; flex: none; margin-top: 1px;
}
.tc-step.done .tc-num { background: var(--success-bg); border-color: transparent; color: #15803d; }
.tc-step-body { min-width: 0; flex: 1; }
.tc-step-name { font-weight: 600; color: var(--text-primary); }
.tc-step-meta {
  font-size: 11px; color: var(--text-muted); margin-top: 1px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tc-step-note { font-size: 12px; color: var(--text-secondary); margin-top: 2px; line-height: 1.6; }
.tc-result { margin-top: 4px; }
.tc-result > summary {
  padding: 2px 0; font-size: 11px; color: var(--primary-color); font-weight: 600;
}
.tc-result > summary:hover { background: transparent; }
.tc-result .markdown-body { font-size: 12px; color: var(--text-secondary); }
/* ── 危险操作确认卡片 ── */
.confirm-card { border-color: rgba(245, 166, 35, .4); }
.cf-head {
  display: flex; align-items: center; gap: 8px; padding: 9px 12px;
  background: var(--warning-bg); border-bottom: 1px solid rgba(245, 166, 35, .25);
  font-size: 12.5px; font-weight: 700; color: #92400e;
}
.cf-head svg { width: 14px; height: 14px; flex: none; }
.cf-body { padding: 10px 12px; font-size: 12.5px; line-height: 1.6; color: var(--text-primary); }
.cf-desc { margin: 0; font-family: inherit; white-space: pre-wrap; word-break: break-word; }
.cf-cmd {
  margin-top: 7px; background: #1d1d22; color: #d6f5dd; border-radius: 7px; padding: 8px 11px;
  font-family: ui-monospace, Consolas, monospace; font-size: 12px; overflow-x: auto;
}
.cf-acts { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border-color); }
.btn {
  display: inline-flex; align-items: center; gap: 6px; border-radius: 7px; padding: 6px 13px;
  font-size: 12.5px; font-weight: 600; cursor: pointer;
  border: 1px solid var(--border-strong); background: var(--surface-color);
  color: var(--text-primary); transition: all .14s;
}
.btn:hover { border-color: #c9c9cf; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(17, 17, 17, .07); }
.btn:disabled { opacity: .55; cursor: not-allowed; transform: none; box-shadow: none; }
.btn-primary { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
.btn-primary:hover { background: var(--primary-hover); border-color: var(--primary-hover); }
.btn-warn { background: var(--warning-color); border-color: var(--warning-color); color: #fff; }
.btn-warn:hover { background: #e0961a; border-color: #e0961a; }
.cf-terminal {
  display: flex; align-items: center; gap: 8px; padding: 9px 12px;
  font-size: 12.5px; font-weight: 600; border-top: 1px solid var(--border-color);
}
.cf-terminal svg { width: 14px; height: 14px; }
.cf-terminal.ok { color: #15803d; background: var(--success-bg); }
.cf-terminal.no { color: #b42318; background: var(--danger-bg); }
/* ── 欢迎态 ── */
.w-hero { max-width: 640px; width: 100%; text-align: center; animation: fadeUp .3s ease; }
.w-ic {
  width: 52px; height: 52px; border-radius: 14px; margin: 0 auto 14px;
  background: #fff; border: 1px solid var(--border-strong);
  display: grid; place-items: center; box-shadow: 0 8px 20px -6px rgba(94, 106, 210, .28);
}
.w-ic img { width: 34px; height: 34px; object-fit: contain; }
.w-title { font-size: 19px; font-weight: 800; color: var(--text-primary); }
.w-sub { font-size: 12.5px; color: var(--text-secondary); margin-top: 6px; line-height: 1.7; }
.w-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
.w-card {
  text-align: left; background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: 10px; padding: 13px 14px; cursor: pointer; transition: all .15s;
}
.w-card:hover {
  border-color: var(--primary-color); background: var(--primary-bg);
  transform: translateY(-2px); box-shadow: 0 6px 14px rgba(94, 106, 210, .12);
}
.wc-t { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.wc-d { font-size: 11.5px; color: var(--text-muted); margin-top: 3px; }

/* ── 未配置引导 ── */
.uc-card {
  max-width: 520px; width: 100%; background: var(--surface-color);
  border: 1px solid var(--border-color); border-radius: 12px; padding: 26px 28px;
  text-align: center; animation: fadeUp .3s ease;
}
.uc-ic {
  width: 46px; height: 46px; border-radius: 12px; background: var(--warning-bg);
  color: #b45309; display: grid; place-items: center; margin: 0 auto 12px;
}
.uc-ic svg { width: 22px; height: 22px; }
.uc-t { font-size: 16px; font-weight: 800; color: var(--text-primary); }
.uc-d { font-size: 12.5px; color: var(--text-secondary); margin-top: 7px; line-height: 1.7; }
.uc-steps { text-align: left; margin: 14px 0 18px; display: flex; flex-direction: column; gap: 8px; }
.uc-step {
  display: flex; gap: 9px; align-items: center; font-size: 12.5px; color: var(--text-primary);
  background: var(--surface-2); border-radius: 8px; padding: 9px 12px;
}
.uc-num {
  width: 17px; height: 17px; border-radius: 50%; background: var(--primary-color);
  color: #fff; font-size: 10.5px; font-weight: 700; display: grid; place-items: center; flex: none;
}
.uc-cta { padding: 9px 22px; font-size: 13px; }
/* ── 输入区卡片 ── */
.chat-input { flex: none; padding: 12px 0 0; }
.ci-card {
  max-width: 860px; margin: 0 auto; background: var(--surface-color);
  border: 1px solid var(--border-strong); border-radius: 12px;
  box-shadow: 0 2px 8px rgba(17, 17, 17, .05);
  transition: border-color .15s, box-shadow .15s;
}
.ci-card:focus-within { border-color: var(--primary-color); box-shadow: 0 0 0 3px rgba(94, 106, 210, .12); }
.ci-card textarea {
  width: 100%; box-sizing: border-box; border: 0; background: transparent; resize: none; outline: none;
  padding: 12px 14px 4px; font-size: 13px; line-height: 1.6; font-family: inherit;
  min-height: 42px; max-height: 160px; color: var(--text-primary); display: block;
}
.ci-card textarea:disabled { color: var(--text-muted); cursor: not-allowed; }
.ci-bar { display: flex; align-items: center; gap: 8px; padding: 6px 10px 9px; }
.ci-hint { font-size: 11px; color: var(--text-muted); }
.ci-send {
  display: inline-flex; align-items: center; gap: 6px; border: 0; border-radius: 8px;
  background: var(--primary-color); color: #fff; font-size: 12.5px; font-weight: 700;
  padding: 7px 14px; cursor: pointer; transition: background .14s;
}
.ci-send:hover { background: var(--primary-hover); }
.ci-send:disabled { opacity: .5; cursor: not-allowed; }
.ci-send svg { width: 13px; height: 13px; }
.ci-stop { background: var(--danger-color); }
.ci-stop:hover { background: #c93a3f; }

/* ── 回到底部浮钮 ── */
.newmsg-btn {
  position: absolute; left: 50%; bottom: 108px; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid var(--border-strong); background: var(--surface-color);
  border-radius: 999px; padding: 6px 13px; font-size: 12px; font-weight: 600;
  color: var(--text-primary); cursor: pointer;
  box-shadow: 0 6px 16px rgba(17, 17, 17, .14); z-index: 5; animation: fadeUp .2s ease;
}
/* ── Markdown 正文 ── */
.markdown-body { font-size: 13px; line-height: 1.65; color: var(--text-primary); }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  margin: 8px 0 4px; font-size: 15px; font-weight: 600;
}
.markdown-body :deep(p) { margin: 4px 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 4px 0; padding-left: 20px; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(code) {
  background: rgba(0, 0, 0, .06); padding: 1px 5px; border-radius: 4px;
  font-size: 12px; font-family: ui-monospace, Consolas, monospace;
}
.markdown-body :deep(pre) {
  background: #1d1d22; border-radius: 8px; overflow-x: auto; margin: 8px 0;
}
.markdown-body :deep(pre code) {
  display: block; padding: 12px 14px; background: none; color: #d4d4d4;
  font-size: 12px; line-height: 1.5;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--border-strong); margin: 8px 0; padding: 4px 12px;
  color: var(--text-muted);
}
.markdown-body :deep(table) { border-collapse: collapse; margin: 8px 0; font-size: 12px; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid var(--border-color); padding: 6px 10px; }
.markdown-body :deep(th) { background: var(--surface-2); font-weight: 600; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid var(--border-color); margin: 8px 0; }

/* ── 思考中 ── */
.typing { display: inline-flex; gap: 4px; padding: 4px 2px; }
.typing i {
  width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted);
  animation: blink 1.2s infinite;
}
.typing i:nth-child(2) { animation-delay: .2s; }
.typing i:nth-child(3) { animation-delay: .4s; }
.tc-spin {
  width: 11px; height: 11px; border: 1.6px solid rgba(94, 106, 210, .25);
  border-top-color: var(--primary-color); border-radius: 50%;
  animation: spin .8s linear infinite; flex: none; margin-top: 2px;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes blink { 0%, 100% { opacity: .25; } 50% { opacity: 1; } }
@keyframes fadeUp { from { opacity: 0; transform: translateY(7px); } }

@media (max-width: 900px) {
  .ai-sidebar { width: 200px; }
  .chat { margin-left: 10px; }
  .m-main { max-width: 92%; }
  .head-ghost { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
