<template>
  <div class="batch-exec">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <h2 class="page-title">批量执行</h2>
      <div class="top-actions">
        <div class="preset-wrap" v-click-outside="closePresets">
          <button class="preset-btn" @click="presetOpen = !presetOpen">
            <el-icon><Collection /></el-icon> 命令预设
            <el-icon class="arrow"><ArrowDown /></el-icon>
          </button>
          <div class="preset-dropdown" v-show="presetOpen">
            <div v-if="!presets.length" class="preset-empty">暂无预设，在后端管理</div>
            <div v-for="p in presets" :key="p.id" class="preset-item" @click="applyPreset(p)">
              <div class="preset-name">{{ p.name }}</div>
              <div class="preset-cmd">{{ p.command }}</div>
            </div>
          </div>
        </div>
        <el-badge :value="historyTotal" :hidden="!historyTotal" :max="99" type="info">
          <el-button size="small" @click="historyVisible = !historyVisible">
            <el-icon><Clock /></el-icon> 历史
          </el-button>
        </el-badge>
      </div>
    </div>

    <!-- 主体 -->
    <div class="main-body">
      <!-- 左侧主机面板 -->
      <div class="host-panel" :class="{ collapsed: panelCollapsed }">
        <div class="panel-header">
          <span class="panel-title" v-show="!panelCollapsed">主机列表</span>
          <button class="collapse-btn" @click="panelCollapsed = !panelCollapsed" :title="panelCollapsed ? '展开' : '折叠'">
            <el-icon><Operation /></el-icon>
          </button>
        </div>
        <div class="host-search" v-show="!panelCollapsed">
          <el-input v-model="hostSearch" placeholder="搜索主机..." clearable size="small" prefix-icon="Search" />
        </div>
        <div class="host-actions" v-show="!panelCollapsed">
          <button @click="selectAll">全选</button>
          <button @click="invertSelect">反选</button>
        </div>
        <div class="host-content" v-show="!panelCollapsed">
          <template v-for="group in filteredHostGroups" :key="group.label">
            <div class="host-group-label">{{ group.label }} ({{ group.items.length }})</div>
            <label
              v-for="host in group.items"
              :key="host.id"
              class="host-item"
              :class="{ disabled: host.status !== '使用中' }"
            >
              <input
                type="checkbox"
                :value="host.id"
                v-model="selectedIds"
                :disabled="host.status !== '使用中'"
              >
              <span class="host-name">{{ host.name }}</span>
              <span class="host-ip">{{ host.ip_address }}</span>
            </label>
          </template>
          <div v-if="!filteredHostGroups.length" class="host-empty">无匹配主机</div>
        </div>
        <div class="host-footer" v-show="!panelCollapsed">
          已选 <strong>{{ selectedIds.length }}</strong> / {{ activeAssets.length }} 台
        </div>
      </div>

      <!-- 中央区域 -->
      <div class="center-area">
        <!-- 命令编辑区 -->
        <div class="command-section">
          <div class="command-header">
            <h4>命令编辑</h4>
            <span class="shortcut-hint"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> 执行</span>
          </div>
          <div class="editor-wrap">
            <div class="line-numbers" ref="lineNumRef">
              <div v-for="n in lineCount" :key="n">{{ n }}</div>
            </div>
            <textarea
              ref="editorRef"
              class="editor-textarea"
              v-model="command"
              :rows="3"
              placeholder="输入要执行的命令，支持多行..."
              @input="updateLineNumbers"
              @scroll="syncScroll"
              @keydown.ctrl.enter.prevent="handleExecute"
            />
          </div>
          <div class="command-footer">
            <div class="timeout-control">
              <span>超时</span>
              <el-slider v-model="timeout" :min="10" :max="300" :step="10" style="width:120px" />
              <span class="timeout-val">{{ timeout }}s</span>
            </div>
            <span class="selected-count">已选 {{ selectedIds.length }} 台</span>
            <el-button @click="handleClear" :disabled="executing">清空</el-button>
            <el-button type="primary" :loading="executing" :disabled="!selectedIds.length || !command.trim()" @click="handleExecute">
              <el-icon><VideoPlay /></el-icon> 执行
            </el-button>
          </div>
        </div>

        <!-- 输出控制台 -->
        <div class="output-section">
          <div class="output-header">
            <h4>输出</h4>
            <div class="output-tabs" v-if="outputs.length">
              <button
                v-for="(item, idx) in outputs"
                :key="item.host_id"
                class="output-tab"
                :class="{ active: activeTab === idx }"
                @click="activeTab = idx"
              >
                <span class="tab-dot" :class="item.done ? (item.exit_code === 0 ? 'success' : 'danger') : 'running'" />
                {{ item.host_name }}
              </button>
            </div>
          </div>

          <div class="console-panels">
            <div v-if="!outputs.length" class="empty-state">
              <el-icon class="empty-icon"><Monitor /></el-icon>
              <p>选择主机并输入命令，点击执行查看结果</p>
            </div>
            <div
              v-for="(item, idx) in outputs"
              :key="item.host_id"
              class="console-panel"
              :class="{ active: activeTab === idx }"
            >
              <div class="console-output" v-text="item.content || '(等待输出...)'"></div>
            </div>
          </div>
        </div>

        <!-- 历史面板 -->
        <div class="history-panel" :class="{ show: historyVisible }">
          <div class="history-header">
            <h4>执行历史</h4>
            <button class="history-close" @click="historyVisible = false">&times;</button>
          </div>
          <div class="history-filters">
            <el-input v-model="historyFilters.keyword" placeholder="搜索命令或主机..." clearable size="small" style="width:200px" @keyup.enter="fetchHistory" />
            <el-select v-model="historyFilters.status" placeholder="全部状态" clearable size="small" style="width:120px" @change="fetchHistory">
              <el-option label="已完成" value="completed" />
              <el-option label="有失败" value="failed" />
            </el-select>
            <el-button size="small" @click="fetchHistory">筛选</el-button>
          </div>
          <div class="history-table-wrap">
            <table class="history-table">
              <thead>
                <tr>
                  <th style="width:50px">ID</th>
                  <th>命令</th>
                  <th>执行主机</th>
                  <th style="width:100px">结果</th>
                  <th style="width:150px">时间</th>
                  <th style="width:70px">操作人</th>
                  <th style="width:50px">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in historyItems" :key="row.id">
                  <td>#{{ row.id }}</td>
                  <td class="cmd-cell">{{ row.command }}</td>
                  <td>{{ row.asset_names }}</td>
                  <td>
                    <el-tag type="success" size="small">{{ row.success_hosts }}</el-tag> /
                    <el-tag type="danger" size="small">{{ row.failed_hosts }}</el-tag>
                  </td>
                  <td>{{ row.created_at }}</td>
                  <td>{{ row.operator || '-' }}</td>
                  <td>
                    <el-button link type="danger" size="small" @click="handleDeleteHistory(row)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </td>
                </tr>
                <tr v-if="!historyItems.length">
                  <td colspan="7" style="text-align:center;color:var(--text-muted);padding:20px">暂无记录</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="history-pagination">
            <el-pagination
              v-model:current-page="historyPage"
              v-model:page-size="historyPageSize"
              :page-sizes="[10, 20, 50]"
              :total="historyTotal"
              layout="total, sizes, prev, pager, next"
              small
              @current-change="fetchHistory"
              @size-change="fetchHistory"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 状态栏 -->
    <div class="status-bar">
      <div class="stat">
        <span class="dot green" /> 共 {{ execSummary?.total ?? 0 }} 台
      </div>
      <div class="stat">
        <span class="dot green" /> 成功 {{ execSummary?.success ?? 0 }}
      </div>
      <div class="stat">
        <span class="dot red" /> 失败 {{ execSummary?.failed ?? 0 }}
      </div>
      <div class="stat" v-if="execDuration" style="margin-left:16px">
        总耗时 {{ execDuration }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, ArrowDown, Clock, VideoPlay, Delete, Monitor, Operation } from '@element-plus/icons-vue'
import { getExecHistory, deleteExecHistory } from '@/api/batch_exec'
import { getPresets } from '@/api/batch_presets'
import { getAssets } from '@/api/assets'
import { getToken } from '@/utils/auth'

// ─── v-click-outside 指令 ──────────────────────────────────
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el._clickOutside = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', el._clickOutside)
  },
}

// ─── 主机面板 ──────────────────────────────────────────────
const allAssets = ref<any[]>([])
const selectedIds = ref<number[]>([])
const hostSearch = ref('')
const panelCollapsed = ref(false)

const activeAssets = computed(() => allAssets.value.filter(a => a.status === '使用中'))

const filteredHostGroups = computed(() => {
  const kw = hostSearch.value.toLowerCase()
  const filter = (list: any[]) => kw ? list.filter(a => a.name.toLowerCase().includes(kw) || a.ip_address.includes(kw)) : list
  const groups = [
    { label: '使用中', items: filter(allAssets.value.filter(a => a.status === '使用中')) },
    { label: '已关机', items: filter(allAssets.value.filter(a => a.status === '已关机')) },
  ]
  return groups.filter(g => g.items.length)
})

function selectAll() {
  selectedIds.value = activeAssets.value.map(a => a.id)
}
function invertSelect() {
  const active = new Set(activeAssets.value.map(a => a.id))
  const sel = new Set(selectedIds.value)
  selectedIds.value = activeAssets.value.filter(a => !sel.has(a.id)).map(a => a.id)
}

// ─── 命令编辑 ──────────────────────────────────────────────
const command = ref('')
const timeout = ref(30)
const editorRef = ref<HTMLTextAreaElement>()
const lineNumRef = ref<HTMLDivElement>()
const lineCount = computed(() => Math.max(command.value.split('\n').length, 1))

function updateLineNumbers() {
  // lineCount is reactive, template auto-updates
}
function syncScroll() {
  if (editorRef.value && lineNumRef.value) {
    lineNumRef.value.scrollTop = editorRef.value.scrollTop
  }
}

// ─── 命令预设 ──────────────────────────────────────────────
const presets = ref<any[]>([])
const presetOpen = ref(false)

function closePresets() {
  presetOpen.value = false
}
function applyPreset(p: any) {
  command.value = p.command
  presetOpen.value = false
  nextTick(updateLineNumbers)
}

async function fetchPresets() {
  try {
    const res: any = await getPresets()
    presets.value = res.data ?? []
  } catch { /* ignore */ }
}

// ─── 执行 ──────────────────────────────────────────────────
const executing = ref(false)
const outputs = ref<any[]>([])
const activeTab = ref(0)
const execSummary = ref<any>(null)
const execDuration = ref('')
let ws: WebSocket | null = null
let execStartTime = 0

function handleClear() {
  command.value = ''
  outputs.value = []
  execSummary.value = null
  execDuration.value = ''
  activeTab.value = 0
}

function handleExecute() {
  if (!selectedIds.value.length || !command.value.trim()) return
  if (executing.value) return

  executing.value = true
  outputs.value = []
  execSummary.value = null
  execDuration.value = ''
  activeTab.value = 0
  execStartTime = Date.now()

  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = getToken()
  const wsUrl = `${wsProtocol}//${location.host}/api/v1/batch-exec/ws/exec`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    ws!.send(JSON.stringify({
      asset_ids: selectedIds.value,
      command: command.value,
      timeout: timeout.value,
    }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'exec_begin') {
        outputs.value = data.hosts.map((h: any) => ({
          host_id: h.id, host_name: h.name, host_ip: h.ip,
          content: '', done: false, exit_code: 0,
        }))
      } else if (data.type === 'exec_result') {
        const item = outputs.value.find(o => o.host_id === data.host_id)
        if (item) {
          let text = ''
          if (data.stdout) text += data.stdout
          if (data.stderr) text += (text ? '\n' : '') + data.stderr
          if (!data.ok) text += (text ? '\n' : '') + `[连接失败] ${data.stderr}`
          item.content = text
          item.done = true
          item.exit_code = data.exit_code
        }
      } else if (data.type === 'exec_done') {
        execSummary.value = { total: data.total, success: data.success, failed: data.failed }
        execDuration.value = ((Date.now() - execStartTime) / 1000).toFixed(2) + 's'
        executing.value = false
        ElMessage.success(`执行完成：成功 ${data.success}，失败 ${data.failed}`)
        fetchHistory()
      } else if (data.type === 'error') {
        ElMessage.error(data.message)
        executing.value = false
      }
    } catch (e) {
      console.error('WebSocket parse error:', e)
    }
  }

  ws.onerror = () => {
    ElMessage.error('WebSocket 连接失败')
    executing.value = false
  }

  ws.onclose = () => {
    if (executing.value) executing.value = false
  }
}

// ─── 历史 ──────────────────────────────────────────────────
const historyVisible = ref(false)
const historyItems = ref<any[]>([])
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)
const historyFilters = reactive({ keyword: '', status: '' })

async function fetchHistory() {
  try {
    const res: any = await getExecHistory({
      ...historyFilters,
      page: historyPage.value,
      page_size: historyPageSize.value,
    })
    historyItems.value = res.data.items
    historyTotal.value = res.data.total
  } catch { /* ignore */ }
}

async function handleDeleteHistory(row: any) {
  await ElMessageBox.confirm(`确定删除执行记录 #${row.id}？`, '删除确认', { type: 'warning' })
  await deleteExecHistory(row.id)
  ElMessage.success('删除成功')
  fetchHistory()
}

// ─── 初始化 & 清理 ────────────────────────────────────────
async function fetchAssets() {
  try {
    const res: any = await getAssets({ page: 1, page_size: 1000 })
    allAssets.value = res.data.items ?? []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载主机失败')
  }
}

onMounted(() => {
  fetchAssets()
  fetchPresets()
  fetchHistory()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style scoped>
.batch-exec {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height) - 32px);
  margin: -16px;
}

/* ── 顶部栏 ── */
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; background: var(--surface-color); border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.top-actions { display: flex; align-items: center; gap: 10px; }

/* ── 预设下拉 ── */
.preset-wrap { position: relative; }
.preset-btn {
  display: inline-flex; align-items: center; gap: 4px; padding: 5px 12px;
  font-size: 13px; border: 1px solid var(--border-color); border-radius: 6px;
  background: var(--surface-color); cursor: pointer; color: var(--text-secondary);
}
.preset-btn:hover { border-color: var(--primary-color); color: var(--primary-color); }
.preset-btn .arrow { font-size: 10px; }
.preset-dropdown {
  position: absolute; top: 100%; right: 0; margin-top: 4px;
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  min-width: 280px; max-height: 320px; overflow-y: auto; z-index: 100;
}
.preset-item {
  padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--border-color);
}
.preset-item:last-child { border-bottom: none; }
.preset-item:hover { background: var(--primary-bg); }
.preset-name { font-size: 13px; font-weight: 600; }
.preset-cmd {
  font-size: 12px; color: var(--text-muted); margin-top: 2px;
  font-family: "Cascadia Code", "Fira Code", monospace; white-space: pre-wrap;
}
.preset-empty { padding: 16px; text-align: center; color: var(--text-muted); font-size: 13px; }

/* ── 主体 ── */
.main-body { display: flex; flex: 1; overflow: hidden; }

/* ── 左侧面板 ── */
.host-panel {
  width: 240px; min-width: 240px; background: var(--surface-color);
  border-right: 1px solid var(--border-color); display: flex; flex-direction: column;
  transition: width 0.3s, min-width 0.3s;
}
.host-panel.collapsed { width: 48px; min-width: 48px; }
.host-panel.collapsed .host-content,
.host-panel.collapsed .host-actions,
.host-panel.collapsed .host-search,
.host-panel.collapsed .panel-title,
.host-panel.collapsed .host-footer { display: none; }
.host-panel.collapsed .collapse-btn { margin: 8px auto; }
.host-panel.collapsed .panel-header { justify-content: center; }
.panel-header {
  padding: 12px 16px; border-bottom: 1px solid var(--border-color);
  display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
}
.panel-title { font-size: 14px; font-weight: 600; }
.collapse-btn {
  background: none; border: none; cursor: pointer; color: var(--text-muted);
  font-size: 16px; padding: 4px; border-radius: 4px;
}
.collapse-btn:hover { background: var(--bg-color); color: var(--text-primary); }
.host-search { padding: 8px 12px; flex-shrink: 0; }
.host-actions { padding: 4px 12px 8px; display: flex; gap: 8px; flex-shrink: 0; }
.host-actions button {
  font-size: 12px; color: var(--primary-color); background: none; border: none;
  cursor: pointer; padding: 2px 4px; border-radius: 4px;
}
.host-actions button:hover { background: var(--primary-bg); }
.host-content { flex: 1; overflow-y: auto; padding: 0 0 12px; }
.host-group-label {
  padding: 8px 16px 4px; font-size: 11px; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;
}
.host-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 16px;
  cursor: pointer; transition: background 0.15s;
}
.host-item:hover { background: var(--bg-color); }
.host-item input[type="checkbox"] { accent-color: var(--primary-color); width: 16px; height: 16px; cursor: pointer; }
.host-name { font-size: 13px; font-weight: 500; }
.host-ip { font-size: 11px; color: var(--text-muted); margin-left: auto; }
.host-item.disabled { opacity: 0.45; pointer-events: none; }
.host-empty { padding: 20px 16px; text-align: center; color: var(--text-muted); font-size: 13px; }
.host-footer {
  padding: 10px 16px; border-top: 1px solid var(--border-color);
  font-size: 12px; color: var(--text-secondary); flex-shrink: 0;
}

/* ── 中央区域 ── */
.center-area { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

/* ── 命令编辑区 ── */
.command-section {
  background: var(--surface-color); border-bottom: 1px solid var(--border-color);
  padding: 16px 20px; flex-shrink: 0;
}
.command-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}
.command-header h4 { font-size: 14px; font-weight: 600; }
.shortcut-hint { font-size: 12px; color: var(--text-muted); }
.shortcut-hint kbd {
  display: inline-block; padding: 1px 6px; font-size: 11px; font-family: monospace;
  background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 3px;
}
.editor-wrap {
  display: flex; border: 1px solid var(--border-color); border-radius: var(--border-radius);
  overflow: hidden; background: #fafbfc;
}
.editor-wrap:focus-within { border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
.line-numbers {
  padding: 10px 0; background: #f5f6f8; text-align: right; user-select: none;
  min-width: 36px; border-right: 1px solid var(--border-color); overflow: hidden;
}
.line-numbers div {
  padding: 0 8px; font-size: 13px; line-height: 20px; color: var(--text-muted);
  font-family: "Cascadia Code", "Fira Code", monospace;
}
.editor-textarea {
  flex: 1; border: none; outline: none; resize: vertical; padding: 10px 12px;
  font-size: 13px; line-height: 20px; font-family: "Cascadia Code", "Fira Code", monospace;
  background: transparent; min-height: 80px; max-height: 200px;
}
.command-footer {
  display: flex; align-items: center; gap: 12px; margin-top: 12px; flex-wrap: wrap;
}
.timeout-control { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary); }
.timeout-val { min-width: 32px; }
.selected-count { font-size: 13px; color: var(--text-muted); margin-left: auto; }

/* ── 输出控制台 ── */
.output-section { flex: 1; display: flex; flex-direction: column; min-height: 0; padding: 0 20px 12px; }
.output-header {
  display: flex; align-items: center; justify-content: space-between; padding: 10px 0; flex-shrink: 0;
}
.output-header h4 { font-size: 14px; font-weight: 600; }
.output-tabs {
  display: flex; gap: 2px; background: var(--bg-color); padding: 3px; border-radius: 8px;
  overflow-x: auto;
}
.output-tab {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px;
  font-size: 12px; font-weight: 500; border: none; border-radius: 6px;
  cursor: pointer; background: transparent; color: var(--text-secondary);
  white-space: nowrap; transition: all 0.15s;
}
.output-tab:hover { background: var(--surface-color); }
.output-tab.active { background: var(--surface-color); color: var(--text-primary); box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.tab-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.tab-dot.success { background: var(--success-color); }
.tab-dot.danger { background: var(--danger-color); }
.tab-dot.running { background: var(--primary-color); animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.console-panels { flex: 1; min-height: 0; }
.console-panel { display: none; height: 100%; }
.console-panel.active { display: flex; }
.console-output {
  flex: 1; background: #1e1e2e; color: #cdd6f4; padding: 14px 16px;
  font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;
  font-size: 13px; line-height: 1.6; overflow: auto; border-radius: var(--border-radius);
  white-space: pre; tab-size: 4;
}
.empty-state {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--text-muted); gap: 8px;
}
.empty-state .empty-icon { font-size: 40px; opacity: 0.4; }
.empty-state p { font-size: 14px; }

/* ── 历史面板 ── */
.history-panel {
  display: none; background: var(--surface-color); border-top: 1px solid var(--border-color);
  max-height: 280px; overflow: hidden; flex-direction: column; flex-shrink: 0;
}
.history-panel.show { display: flex; }
.history-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 20px; border-bottom: 1px solid var(--border-color); flex-shrink: 0;
}
.history-header h4 { font-size: 14px; font-weight: 600; }
.history-close {
  background: none; border: none; cursor: pointer; font-size: 18px;
  color: var(--text-muted); padding: 2px 6px; border-radius: 4px;
}
.history-close:hover { background: var(--bg-color); }
.history-filters {
  display: flex; gap: 8px; padding: 8px 20px; border-bottom: 1px solid var(--border-color); flex-shrink: 0;
}
.history-table-wrap { flex: 1; overflow: auto; }
.history-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.history-table th {
  padding: 8px 16px; text-align: left; font-weight: 600; font-size: 12px;
  color: var(--text-secondary); background: var(--bg-color); position: sticky; top: 0;
  border-bottom: 1px solid var(--border-color);
}
.history-table td { padding: 8px 16px; border-bottom: 1px solid var(--border-color); }
.history-table tr:hover { background: var(--primary-bg); }
.history-table .cmd-cell { font-family: "Cascadia Code", monospace; font-size: 12px; }
.history-pagination {
  display: flex; justify-content: flex-end; padding: 8px 20px; flex-shrink: 0;
}

/* ── 状态栏 ── */
.status-bar {
  display: flex; align-items: center; gap: 16px; padding: 8px 20px;
  background: var(--surface-color); border-top: 1px solid var(--border-color);
  font-size: 12px; color: var(--text-secondary); flex-shrink: 0;
}
.stat { display: flex; align-items: center; gap: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.green { background: var(--success-color); }
.dot.red { background: var(--danger-color); }
</style>
