<template>
  <div class="batch-exec">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <div class="top-left">
        <h2 class="page-title">批量执行</h2>
        <span class="top-meta">在线 <b>{{ activeAssets.length }}</b> / {{ allAssets.length }} 台</span>
      </div>
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
        <el-button size="small" :disabled="!outputs.length" @click="exportResults">
          <el-icon><Download /></el-icon> 导出结果
        </el-button>
      </div>
    </div>

    <!-- 主体 -->
    <div class="main-body">
      <!-- 左侧主机面板 -->
      <div class="host-panel" :class="{ collapsed: panelCollapsed }">
        <div class="panel-header">
          <span class="panel-title" v-show="!panelCollapsed">目标主机</span>
          <button class="collapse-btn" @click="panelCollapsed = !panelCollapsed" :title="panelCollapsed ? '展开' : '折叠'">
            <el-icon><Operation /></el-icon>
          </button>
        </div>
        <template v-if="!panelCollapsed">
          <div class="host-search">
            <el-input v-model="hostSearch" placeholder="搜索名称 / IP / 类型..." clearable size="small" prefix-icon="Search" />
          </div>
          <div class="quick-select">
            <span class="quick-chip" @click="selectAllOnline">全选在线</span>
            <span class="quick-chip" @click="invertSelect">反选</span>
            <span class="quick-chip" @click="clearSelected">清空</span>
          </div>
          <div class="host-tree">
            <div v-for="group in hostGroups" :key="group.label" class="tree-group">
              <div class="tree-group-header" @click="toggleGroup(group.label)">
                <el-icon class="g-arrow" :class="{ closed: collapsedGroups.has(group.label) }"><ArrowDown /></el-icon>
                <span class="g-label">{{ group.label }}</span>
                <span class="g-count">
                  <span class="sel-ind" v-if="groupSelectedCount(group)">{{ groupSelectedCount(group) }}</span>/{{ group.items.length }}
                </span>
              </div>
              <div class="tree-items" v-show="!collapsedGroups.has(group.label)">
                <div
                  v-for="host in group.items"
                  :key="host.id"
                  class="host-item"
                  :class="{ selected: selectedIds.includes(host.id), offline: host.status !== '使用中' }"
                  @click="toggleHost(host)"
                >
                  <span class="cbx"><el-icon v-if="selectedIds.includes(host.id)"><Check /></el-icon></span>
                  <span class="h-status" :class="host.status === '使用中' ? 'online' : 'offline'"></span>
                  <span class="host-name">{{ host.name }}</span>
                  <span class="host-ip">{{ host.ip_address }}</span>
                </div>
              </div>
            </div>
            <div v-if="!hostGroups.length" class="host-empty">无匹配主机</div>
          </div>
          <!-- 已选 chips -->
          <div class="selected-area" v-if="selectedAssets.length">
            <div class="sa-header">
              <span class="sa-title">已选 {{ selectedAssets.length }} 台</span>
              <span class="sa-clear" @click="clearSelected">清空</span>
            </div>
            <div class="sa-chips">
              <span v-for="a in selectedAssets" :key="a.id" class="sa-chip">
                {{ a.name }}
                <el-icon class="x" @click="removeSelected(a.id)"><Close /></el-icon>
              </span>
            </div>
          </div>
          <div class="host-footer" v-else>
            已选 <strong>0</strong> / {{ activeAssets.length }} 台
          </div>
        </template>
      </div>

      <!-- 中央区域 -->
      <div class="center-area">
        <!-- 命令编辑区 -->
        <div class="editor-card">
          <div class="editor-card-header">
            <h4>命令编辑</h4>
            <div class="editor-tools">
              <button class="tool-btn" :class="{ on: highlightOn }" @click="highlightOn = !highlightOn">高亮</button>
              <button class="tool-btn" :disabled="!command.trim()" @click="saveAsPreset">存为预设</button>
              <span class="shortcut-hint"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> 执行</span>
            </div>
          </div>
          <div class="code-editor">
            <div class="gutter" ref="lineNumRef">
              <div v-for="n in lineCount" :key="n">{{ n }}</div>
            </div>
            <div class="editor-stack" :style="{ height: editorHeight }">
              <pre class="editor-highlight" ref="highlightRef" v-html="highlightedCommand"></pre>
              <textarea
                ref="editorRef"
                class="editor-textarea"
                v-model="command"
                placeholder="输入要执行的命令，支持多行..."
                spellcheck="false"
                @scroll="syncScroll"
                @keydown.ctrl.enter.prevent="handleExecute()"
              />
            </div>
          </div>

          <!-- 危险命令警告 -->
          <div class="danger-banner" v-if="dangerHits.length">
            <el-icon><WarningFilled /></el-icon>
            检测到高危命令
            <span class="d-cmd" v-for="h in dangerHits" :key="h">{{ h }}</span>
            ，将在 <b>{{ selectedIds.length }}</b> 台主机上执行，执行前需二次确认
          </div>

          <!-- 执行选项条 -->
          <div class="exec-options">
            <div class="opt">
              <span class="opt-label">超时</span>
              <el-input-number v-model="timeout" :min="10" :max="300" :step="10" size="small" controls-position="right" style="width:84px" />
              <span>s</span>
            </div>
            <div class="opt">
              <span class="opt-label">并发</span>
              <el-input-number v-model="concurrency" :min="0" :max="50" size="small" controls-position="right" style="width:74px" />
              <span class="opt-hint">0=不限</span>
            </div>
            <div class="opt">
              <span class="opt-label">分批</span>
              <el-select v-model="batchSize" size="small" style="width:150px">
                <el-option :value="0" label="不分批" />
                <el-option :value="2" label="每批 2 台滚动" />
                <el-option :value="3" label="每批 3 台滚动" />
                <el-option :value="5" label="每批 5 台滚动" />
                <el-option :value="10" label="每批 10 台滚动" />
              </el-select>
            </div>
            <div class="opt">
              <span class="opt-label">失败自动重试</span>
              <el-switch v-model="autoRetry" size="small" />
              <span class="opt-hint">1 次</span>
            </div>
            <div class="exec-buttons">
              <span class="selected-count">已选 {{ selectedIds.length }} 台</span>
              <el-button size="small" @click="handleClear" :disabled="executing">清空</el-button>
              <el-button type="primary" size="small" :loading="executing" :disabled="!selectedIds.length || !command.trim()" @click="handleExecute()">
                <el-icon><VideoPlay /></el-icon> 执行
              </el-button>
            </div>
          </div>
        </div>

        <!-- 执行结果区 -->
        <div class="result-section" v-if="outputs.length">
          <!-- 总览条 -->
          <div class="summary-bar">
            <div class="sum-stat success"><span class="dot"></span>成功 {{ statSuccess }}</div>
            <div class="sum-stat failed"><span class="dot"></span>失败 {{ statFailed }}</div>
            <div class="sum-stat running" v-if="statRunning"><span class="dot"></span>执行中 {{ statRunning }}</div>
            <div class="sum-stat pending" v-if="statSkipped"><span class="dot"></span>已跳过 {{ statSkipped }}</div>
            <div class="progress-wrap">
              <div class="progress-track">
                <div class="progress-fill-s" :style="{ width: progressPct.success + '%' }"></div>
                <div class="progress-fill-f" :style="{ width: progressPct.failed + '%' }"></div>
              </div>
              <span class="progress-pct">{{ statDone }}/{{ outputs.length }} · {{ Math.round(progressPct.done) }}%</span>
            </div>
            <button class="btn-stop" v-if="executing" :disabled="cancelling" @click="handleCancel">
              {{ cancelling ? '取消中...' : '■ 停止执行' }}
            </button>
          </div>

          <!-- 视图工具栏 -->
          <div class="result-toolbar">
            <div class="view-switch">
              <button class="view-tab" :class="{ active: viewMode === 'single' }" @click="viewMode = 'single'">单机视图</button>
              <button class="view-tab" :class="{ active: viewMode === 'agg' }" @click="viewMode = 'agg'">聚合视图</button>
              <button class="view-tab" :class="{ active: viewMode === 'compare' }" @click="viewMode = 'compare'">对比视图</button>
            </div>
            <div class="rt-spacer"></div>
            <el-checkbox v-model="failOnly" size="small" label="只看失败" />
            <el-input v-model="outputSearch" placeholder="在输出中搜索..." clearable size="small" prefix-icon="Search" style="width:200px" />
            <el-button size="small" :disabled="!activeOutput" @click="copyActiveOutput">复制</el-button>
          </div>

          <!-- 单机视图 -->
          <div class="result-body" v-show="viewMode === 'single'">
            <div class="result-list">
              <template v-for="g in groupedOutputs" :key="g.label">
                <div class="rl-group-label" v-if="g.items.length">{{ g.label }} ({{ g.items.length }})</div>
                <div
                  v-for="item in g.items"
                  :key="item.host_id"
                  class="rl-item"
                  :class="{ active: activeHostId === item.host_id, 'is-fail': item.done && !item.skipped && item.exit_code !== 0 }"
                  @click="activeHostId = item.host_id"
                >
                  <span class="rl-dot" :class="dotClass(item)"></span>
                  <span class="rl-name">{{ item.host_name }}</span>
                  <span class="rl-time" v-if="item.duration != null">{{ item.duration }}s</span>
                  <span class="retry" v-if="item.done && !item.skipped && item.exit_code !== 0" @click.stop="retryHost(item)">重试</span>
                </div>
              </template>
            </div>
            <div class="console-panel" v-if="activeOutput">
              <div class="console-head">
                <span class="ch-dot" :class="dotClass(activeOutput)"></span>
                <span class="ch-host">{{ activeOutput.host_name }}</span>
                <span class="ch-ip">{{ activeOutput.host_ip }}</span>
                <span class="ch-exit" :class="{ ok: activeOutput.exit_code === 0 }" v-if="activeOutput.done && !activeOutput.skipped">exit {{ activeOutput.exit_code }}</span>
                <span class="ch-exit skipped" v-if="activeOutput.skipped">已跳过</span>
                <div class="ch-actions">
                  <button class="ch-btn" v-if="activeOutput.done && !activeOutput.skipped && activeOutput.exit_code !== 0" @click="retryHost(activeOutput)">↻ 重试</button>
                </div>
              </div>
              <div class="console-body" v-html="renderOutput(activeOutput.content, outputSearch)"></div>
            </div>
          </div>

          <!-- 聚合视图 -->
          <div class="agg-body" v-show="viewMode === 'agg'">
            <div v-for="item in aggOutputs" :key="item.host_id" class="agg-section">
              <div class="agg-head" @click="activeHostId = item.host_id; viewMode = 'single'">
                <span class="rl-dot" :class="dotClass(item)"></span>
                <span class="ch-host">{{ item.host_name }}</span>
                <span class="ch-ip">{{ item.host_ip }}</span>
                <span class="ch-exit" :class="{ ok: item.exit_code === 0 }" v-if="item.done && !item.skipped">exit {{ item.exit_code }}</span>
                <span class="rl-time" v-if="item.duration != null">{{ item.duration }}s</span>
              </div>
              <div class="console-body" v-html="renderOutput(item.content, outputSearch)"></div>
            </div>
          </div>

          <!-- 对比视图 -->
          <div class="compare-body" v-show="viewMode === 'compare'">
            <div class="compare-bar">
              <el-select v-model="compareA" size="small" placeholder="主机 A" style="width:180px">
                <el-option v-for="o in doneOutputs" :key="o.host_id" :value="o.host_id" :label="o.host_name" />
              </el-select>
              <span class="compare-vs">vs</span>
              <el-select v-model="compareB" size="small" placeholder="主机 B" style="width:180px">
                <el-option v-for="o in doneOutputs" :key="o.host_id" :value="o.host_id" :label="o.host_name" />
              </el-select>
              <span class="compare-hint" v-if="compareDiffCount">差异 {{ compareDiffCount }} 行</span>
            </div>
            <div class="compare-table-wrap" v-if="compareRows.length">
              <table class="compare-table">
                <tr v-for="(row, i) in compareRows" :key="i" :class="{ diff: row.diff }">
                  <td class="ln">{{ i + 1 }}</td>
                  <td class="cc">{{ row.a }}</td>
                  <td class="cc">{{ row.b }}</td>
                </tr>
              </table>
            </div>
            <div class="compare-empty" v-else>选择两台已完成的主机进行输出对比</div>
          </div>
        </div>

        <!-- 空状态 -->
        <div class="output-empty" v-else>
          <el-icon class="empty-icon"><Monitor /></el-icon>
          <p>选择主机并输入命令，点击执行查看结果</p>
        </div>
      </div>
    </div>

    <!-- 状态栏 -->
    <div class="status-bar">
      <div class="sb-stat">目标主机 <b>{{ outputs.length || selectedIds.length }}</b> 台</div>
      <template v-if="outputs.length">
        <div class="sb-stat">成功 <b class="ok">{{ statSuccess }}</b></div>
        <div class="sb-stat">失败 <b class="err">{{ statFailed }}</b></div>
        <div class="sb-stat" v-if="statSkipped">跳过 <b>{{ statSkipped }}</b></div>
      </template>
      <div class="sb-stat" v-if="execDuration">总耗时 <b>{{ execDuration }}</b></div>
      <div class="sb-stat" v-if="avgDuration">平均单机 <b>{{ avgDuration }}</b></div>
      <div class="sb-right" v-if="cancelledFlag">本次执行已被手动停止</div>
    </div>

    <!-- 历史抽屉 -->
    <div class="history-drawer" :class="{ show: historyVisible }">
      <div class="hd-header">
        <h4>执行历史</h4>
        <button class="hd-close" @click="historyVisible = false">&times;</button>
      </div>
      <div class="hd-filters">
        <el-input v-model="historyFilters.keyword" placeholder="搜索命令或主机..." clearable size="small" style="flex:1" @keyup.enter="fetchHistory" />
        <el-select v-model="historyFilters.status" placeholder="全部状态" clearable size="small" style="width:110px" @change="fetchHistory">
          <el-option label="已完成" value="completed" />
          <el-option label="有失败" value="failed" />
        </el-select>
        <el-button size="small" @click="fetchHistory">筛选</el-button>
      </div>
      <div class="hd-list">
        <div v-for="row in historyItems" :key="row.id" class="hd-item">
          <div class="hd-cmd">{{ row.command }}</div>
          <div class="hd-meta">
            <span class="hd-tag" :class="row.failed_hosts ? 'warn' : 'ok'">
              {{ row.failed_hosts ? row.success_hosts + '/' + row.total_hosts + ' 成功' : '全部成功' }}
            </span>
            <span>{{ row.total_hosts }} 台 · {{ row.operator || '-' }} · {{ row.created_at }}</span>
            <div class="hd-acts">
              <button class="hd-act" @click="reuseHistory(row)">复用命令</button>
              <button class="hd-act retry-fail" @click="handleDeleteHistory(row)">删除</button>
            </div>
          </div>
        </div>
        <div v-if="!historyItems.length" class="hd-empty">暂无记录</div>
      </div>
      <div class="hd-pagination">
        <el-pagination
          v-model:current-page="historyPage"
          v-model:page-size="historyPageSize"
          :page-sizes="[10, 20, 50]"
          :total="historyTotal"
          layout="total, prev, pager, next"
          small
          @current-change="fetchHistory"
          @size-change="fetchHistory"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection, ArrowDown, Clock, VideoPlay, Monitor, Operation,
  Download, Check, Close, WarningFilled,
} from '@element-plus/icons-vue'
import { getExecHistory, deleteExecHistory } from '@/api/batch_exec'
import { getPresets, createPreset } from '@/api/batch_presets'
import { getAssets } from '@/api/assets'

// ─── v-click-outside 指令 ──────────────────────────────────
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    ;(el as any)._clickOutside = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    document.addEventListener('click', (el as any)._clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', (el as any)._clickOutside)
  },
}

// ─── 主机面板 ──────────────────────────────────────────────
const allAssets = ref<any[]>([])
const selectedIds = ref<number[]>([])
const hostSearch = ref('')
const panelCollapsed = ref(false)
const collapsedGroups = ref<Set<string>>(new Set())

const activeAssets = computed(() => allAssets.value.filter(a => a.status === '使用中'))

const hostGroups = computed(() => {
  const kw = hostSearch.value.trim().toLowerCase()
  const match = (a: any) =>
    !kw ||
    a.name.toLowerCase().includes(kw) ||
    a.ip_address.includes(kw) ||
    (a.asset_type || '').toLowerCase().includes(kw)
  const map = new Map<string, any[]>()
  for (const a of allAssets.value.filter(match)) {
    const key = a.asset_type || '未分组'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(a)
  }
  return [...map.entries()].map(([label, items]) => ({ label, items }))
})

const selectedAssets = computed(() => allAssets.value.filter(a => selectedIds.value.includes(a.id)))

function toggleHost(host: any) {
  if (host.status !== '使用中') return
  const i = selectedIds.value.indexOf(host.id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(host.id)
}
function toggleGroup(label: string) {
  if (collapsedGroups.value.has(label)) collapsedGroups.value.delete(label)
  else collapsedGroups.value.add(label)
}
function groupSelectedCount(g: { items: any[] }) {
  return g.items.filter(i => selectedIds.value.includes(i.id)).length
}
function selectAllOnline() {
  selectedIds.value = activeAssets.value.map(a => a.id)
}
function invertSelect() {
  const sel = new Set(selectedIds.value)
  selectedIds.value = activeAssets.value.filter(a => !sel.has(a.id)).map(a => a.id)
}
function clearSelected() {
  selectedIds.value = []
}
function removeSelected(id: number) {
  selectedIds.value = selectedIds.value.filter(i => i !== id)
}

// ─── 命令编辑（高亮 + 危险命令检测）─────────────────────────
const command = ref('')
const highlightOn = ref(true)
const timeout = ref(30)
const concurrency = ref(0)
const batchSize = ref(0)
const autoRetry = ref(false)
const editorRef = ref<HTMLTextAreaElement>()
const lineNumRef = ref<HTMLDivElement>()
const highlightRef = ref<HTMLElement>()

const lineCount = computed(() => Math.max(command.value.split('\n').length, 1))
const editorHeight = computed(() => Math.min(Math.max(lineCount.value * 20 + 20, 80), 220) + 'px')

const DANGER_PATTERNS: { re: RegExp; label: string }[] = [
  { re: /\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+\S*/, label: 'rm -rf' },
  { re: /\bmkfs\b[^&|;]*/, label: 'mkfs 格式化' },
  { re: /\bdd\s+if=\S+\s+of=\/dev\/\S+/, label: 'dd 写磁盘' },
  { re: /\b(shutdown|poweroff|reboot|halt)\b/, label: '关机/重启' },
  { re: /:\(\)\s*\{/, label: 'fork 炸弹' },
  { re: />\s*\/dev\/sd[a-z]/, label: '覆写磁盘设备' },
  { re: /\bchmod\s+-R\s+777\s+\//, label: '递归放权 /' },
  { re: /\b(killall|pkill)\s+-9\b/, label: '强制杀进程' },
]

const dangerHits = computed(() =>
  DANGER_PATTERNS.filter(p => p.re.test(command.value)).map(p => p.label),
)

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlightLine(line: string): string {
  const esc = escapeHtml(line)
  if (/^\s*#/.test(line)) return `<span class="tk-comment">${esc}</span>`
  let html = esc
  // 字符串
  html = html.replace(/("[^"]*"|'[^']*')/g, '<span class="tk-str">$1</span>')
  // 高危命令
  for (const p of DANGER_PATTERNS) {
    html = html.replace(p.re, m => `<span class="tk-danger">${m}</span>`)
  }
  // 参数
  html = html.replace(/(?<![\w-])(--?[a-zA-Z][\w-]*)/g, '<span class="tk-flag">$1</span>')
  // 管道
  html = html.replace(/\|/g, '<span class="tk-pipe">|</span>')
  // 行首命令
  html = html.replace(/^(\s*)([a-zA-Z0-9_./-]+)/, '$1<span class="tk-cmd">$2</span>')
  return html
}

const highlightedCommand = computed(() => {
  const lines = command.value.split('\n')
  const body = highlightOn.value ? lines.map(highlightLine).join('\n') : escapeHtml(command.value)
  return body + '\n'
})

function syncScroll() {
  if (!editorRef.value) return
  if (lineNumRef.value) lineNumRef.value.scrollTop = editorRef.value.scrollTop
  if (highlightRef.value) highlightRef.value.scrollTop = editorRef.value.scrollTop
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
}
async function saveAsPreset() {
  try {
    const { value } = await ElMessageBox.prompt('请输入预设名称', '存为预设', {
      inputPlaceholder: '例如：清理临时日志',
      inputValidator: (v: string) => !!v?.trim() || '名称不能为空',
    })
    await createPreset({ name: value.trim(), command: command.value })
    ElMessage.success('已保存为预设')
    fetchPresets()
  } catch { /* 用户取消 */ }
}
async function fetchPresets() {
  try {
    const res: any = await getPresets()
    presets.value = res.data ?? []
  } catch { /* ignore */ }
}

// ─── 执行 ──────────────────────────────────────────────────
interface HostOutput {
  host_id: number
  host_name: string
  host_ip: string
  content: string
  done: boolean
  skipped: boolean
  exit_code: number
  duration: number | null
}

const executing = ref(false)
const cancelling = ref(false)
const cancelledFlag = ref(false)
const outputs = ref<HostOutput[]>([])
const activeHostId = ref<number | null>(null)
const execDuration = ref('')
let ws: WebSocket | null = null
let execStartTime = 0
let retriedOnce = false

const statSuccess = computed(() => outputs.value.filter(o => o.done && !o.skipped && o.exit_code === 0).length)
const statFailed = computed(() => outputs.value.filter(o => o.done && !o.skipped && o.exit_code !== 0).length)
const statSkipped = computed(() => outputs.value.filter(o => o.skipped).length)
const statRunning = computed(() => outputs.value.filter(o => !o.done).length)
const statDone = computed(() => outputs.value.filter(o => o.done).length)
const progressPct = computed(() => {
  const total = outputs.value.length || 1
  return {
    success: (statSuccess.value / total) * 100,
    failed: (statFailed.value / total) * 100,
    done: (statDone.value / total) * 100,
  }
})
const avgDuration = computed(() => {
  const ds = outputs.value.filter(o => o.duration != null).map(o => o.duration!)
  if (!ds.length) return ''
  return (ds.reduce((a, b) => a + b, 0) / ds.length).toFixed(2) + 's'
})

const activeOutput = computed(() =>
  outputs.value.find(o => o.host_id === activeHostId.value) ?? outputs.value[0] ?? null,
)

const failedHostIds = computed(() =>
  outputs.value.filter(o => o.done && !o.skipped && o.exit_code !== 0).map(o => o.host_id),
)

function dotClass(item: HostOutput) {
  if (item.skipped) return 'skip'
  if (!item.done) return 'run'
  return item.exit_code === 0 ? 'ok' : 'err'
}

function handleClear() {
  command.value = ''
  outputs.value = []
  execDuration.value = ''
  cancelledFlag.value = false
  activeHostId.value = null
}

async function handleExecute(targetIds?: number[]) {
  const ids = targetIds ?? selectedIds.value
  if (!ids.length || !command.value.trim() || executing.value) return

  // 高危命令二次确认（仅首次全量执行时）
  if (!targetIds && dangerHits.value.length) {
    try {
      await ElMessageBox.confirm(
        `检测到高危命令：${dangerHits.value.join('、')}，将在 ${ids.length} 台主机上执行。确认继续？`,
        '高危操作确认',
        { type: 'warning', confirmButtonText: '仍要执行', cancelButtonText: '取消' },
      )
    } catch { return }
  }
  retriedOnce = false
  runExec(ids, false)
}

function retryHost(item: HostOutput) {
  if (executing.value) return
  runExec([item.host_id], true)
}

function runExec(ids: number[], merge: boolean) {
  executing.value = true
  cancelling.value = false
  cancelledFlag.value = false
  if (!merge) {
    outputs.value = []
    execDuration.value = ''
  }
  execStartTime = Date.now()

  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${location.host}/api/v1/batch-exec/ws/exec`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    ws!.send(JSON.stringify({
      asset_ids: ids,
      command: command.value,
      timeout: timeout.value,
      concurrency: concurrency.value,
      batch_size: batchSize.value,
    }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'exec_begin') {
        const fresh: HostOutput[] = data.hosts.map((h: any) => ({
          host_id: h.id, host_name: h.name, host_ip: h.ip,
          content: '', done: false, skipped: false, exit_code: 0, duration: null,
        }))
        if (merge) {
          // 重试：替换对应主机条目，保持原顺序
          for (const f of fresh) {
            const idx = outputs.value.findIndex(o => o.host_id === f.host_id)
            if (idx >= 0) outputs.value[idx] = f
            else outputs.value.push(f)
          }
        } else {
          outputs.value = fresh
          activeHostId.value = fresh[0]?.host_id ?? null
        }
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
          item.duration = data.duration ?? null
        }
      } else if (data.type === 'exec_skip') {
        const item = outputs.value.find(o => o.host_id === data.host_id)
        if (item) {
          item.done = true
          item.skipped = true
          item.content = '(已取消，未执行)'
        }
      } else if (data.type === 'exec_done') {
        execDuration.value = ((Date.now() - execStartTime) / 1000).toFixed(2) + 's'
        executing.value = false
        cancelling.value = false
        cancelledFlag.value = !!data.cancelled
        if (data.cancelled) {
          ElMessage.warning(`执行已停止：成功 ${data.success}，失败 ${data.failed}，跳过 ${data.skipped ?? 0}`)
        } else {
          ElMessage.success(`执行完成：成功 ${data.success}，失败 ${data.failed}`)
        }
        fetchHistory()
        // 失败自动重试（仅一次）
        if (!data.cancelled && autoRetry.value && !retriedOnce && failedHostIds.value.length) {
          retriedOnce = true
          ElMessage.info(`自动重试 ${failedHostIds.value.length} 台失败主机...`)
          runExec(failedHostIds.value, true)
        }
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

function handleCancel() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  cancelling.value = true
  ws.send(JSON.stringify({ type: 'exec_cancel' }))
}

// ─── 结果视图 ──────────────────────────────────────────────
const viewMode = ref<'single' | 'agg' | 'compare'>('single')
const failOnly = ref(false)
const outputSearch = ref('')

const groupedOutputs = computed(() => {
  const list = outputs.value
  const failed = list.filter(o => o.done && !o.skipped && o.exit_code !== 0)
  if (failOnly.value) return [{ label: '失败', items: failed }]
  return [
    { label: '失败', items: failed },
    { label: '执行中', items: list.filter(o => !o.done) },
    { label: '已跳过', items: list.filter(o => o.skipped) },
    { label: '成功', items: list.filter(o => o.done && !o.skipped && o.exit_code === 0) },
  ]
})

const aggOutputs = computed(() =>
  failOnly.value ? outputs.value.filter(o => o.done && !o.skipped && o.exit_code !== 0) : outputs.value,
)

const doneOutputs = computed(() => outputs.value.filter(o => o.done && !o.skipped))

const compareA = ref<number | null>(null)
const compareB = ref<number | null>(null)

const compareRows = computed(() => {
  const a = outputs.value.find(o => o.host_id === compareA.value)
  const b = outputs.value.find(o => o.host_id === compareB.value)
  if (!a || !b || a === b) return []
  const la = (a.content || '').split('\n')
  const lb = (b.content || '').split('\n')
  const n = Math.max(la.length, lb.length)
  const rows: { a: string; b: string; diff: boolean }[] = []
  for (let i = 0; i < n; i++) {
    const x = la[i] ?? ''
    const y = lb[i] ?? ''
    rows.push({ a: x, b: y, diff: x !== y })
  }
  return rows
})

const compareDiffCount = computed(() => compareRows.value.filter(r => r.diff).length)

function renderOutput(text: string, kw: string): string {
  let html = escapeHtml(text || '(等待输出...)')
  const k = kw.trim()
  if (k) {
    const esc = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    html = html.replace(new RegExp(esc, 'gi'), m => `<span class="t-hl">${m}</span>`)
  }
  return html
}

async function copyActiveOutput() {
  if (!activeOutput.value) return
  try {
    await navigator.clipboard.writeText(activeOutput.value.content || '')
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function exportResults() {
  const lines: string[] = [
    `# 批量执行结果 ${new Date().toLocaleString()}`,
    `# 命令: ${command.value}`,
    '',
  ]
  for (const o of outputs.value) {
    lines.push(
      '='.repeat(60),
      `[${o.host_name}] ${o.host_ip}  exit=${o.skipped ? 'skipped' : o.exit_code}  耗时=${o.duration ?? '-'}s`,
      o.content || '(无输出)',
      '',
    )
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `batch-exec-${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(a.href)
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

function reuseHistory(row: any) {
  command.value = row.command
  const ids = String(row.asset_ids || '').split(',').map(Number).filter(Boolean)
  const valid = ids.filter(id => activeAssets.value.some(a => a.id === id))
  if (valid.length) selectedIds.value = valid
  historyVisible.value = false
  ElMessage.success(`已填入命令${valid.length ? `，并选中 ${valid.length} 台主机` : ''}`)
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
  position: relative;
}

/* ── 顶部栏 ── */
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; background: var(--surface-color); border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.top-left { display: flex; align-items: center; gap: 14px; }
.top-meta { font-size: 12px; color: var(--text-muted); }
.top-meta b { color: var(--text-secondary); }
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
.preset-item { padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--border-color); }
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
  width: 260px; min-width: 260px; background: var(--surface-color);
  border-right: 1px solid var(--border-color); display: flex; flex-direction: column;
  transition: width 0.3s, min-width 0.3s;
}
.host-panel.collapsed { width: 48px; min-width: 48px; }
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
.quick-select { display: flex; gap: 6px; padding: 0 12px 8px; flex-shrink: 0; flex-wrap: wrap; }
.quick-chip {
  font-size: 11px; padding: 3px 10px; border-radius: 10px; border: 1px solid var(--border-color);
  background: var(--surface-color); color: var(--text-secondary); cursor: pointer; transition: all 0.15s;
}
.quick-chip:hover { border-color: var(--primary-color); color: var(--primary-color); }
.host-tree { flex: 1; overflow-y: auto; padding-bottom: 8px; }
.tree-group-header {
  display: flex; align-items: center; gap: 6px; padding: 7px 14px; cursor: pointer;
  font-size: 12px; font-weight: 600; color: var(--text-secondary); user-select: none;
}
.tree-group-header:hover { background: var(--bg-color); }
.g-arrow { font-size: 10px; color: var(--text-muted); transition: transform 0.2s; }
.g-arrow.closed { transform: rotate(-90deg); }
.g-count { margin-left: auto; font-size: 11px; color: var(--text-muted); font-weight: 400; }
.sel-ind { color: var(--primary-color); font-weight: 600; }
.host-item {
  display: flex; align-items: center; gap: 8px; padding: 5px 14px 5px 28px;
  cursor: pointer; transition: background 0.12s;
}
.host-item:hover { background: var(--bg-color); }
.host-item.selected { background: var(--primary-bg); }
.cbx {
  width: 15px; height: 15px; border: 1.5px solid #ccc; border-radius: 3px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center; font-size: 10px; color: #fff;
}
.host-item.selected .cbx { background: var(--primary-color); border-color: var(--primary-color); }
.h-status { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.h-status.online { background: var(--success-color); }
.h-status.offline { background: #d1d5db; }
.host-name { font-size: 12.5px; font-weight: 500; }
.host-ip { font-size: 11px; color: var(--text-muted); margin-left: auto; font-family: "Cascadia Code", monospace; }
.host-item.offline { opacity: 0.45; cursor: not-allowed; }
.host-empty { padding: 20px 16px; text-align: center; color: var(--text-muted); font-size: 13px; }
.host-footer {
  padding: 10px 16px; border-top: 1px solid var(--border-color);
  font-size: 12px; color: var(--text-secondary); flex-shrink: 0;
}

/* 已选 chips 区 */
.selected-area {
  border-top: 1px solid var(--border-color); padding: 10px 12px; flex-shrink: 0;
  max-height: 130px; overflow-y: auto; background: #fcfcfd;
}
.sa-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.sa-title { font-size: 11px; font-weight: 700; color: var(--text-secondary); }
.sa-clear { font-size: 11px; color: var(--danger-color); cursor: pointer; }
.sa-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.sa-chip {
  display: inline-flex; align-items: center; gap: 4px; font-size: 11px; padding: 2px 5px 2px 8px;
  background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 5px; color: var(--text-secondary);
}
.sa-chip .x { cursor: pointer; color: var(--text-muted); font-size: 11px; }
.sa-chip .x:hover { color: var(--danger-color); }

/* ── 中央区域 ── */
.center-area { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow-y: auto; }

/* ── 命令编辑卡片 ── */
.editor-card {
  background: var(--surface-color); border-bottom: 1px solid var(--border-color);
  padding: 14px 20px 12px; flex-shrink: 0;
}
.editor-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.editor-card-header h4 { font-size: 13px; font-weight: 700; }
.editor-tools { display: flex; align-items: center; gap: 6px; }
.tool-btn {
  font-size: 11px; padding: 3px 9px; border-radius: 5px; border: 1px solid var(--border-color);
  background: var(--surface-color); color: var(--text-secondary); cursor: pointer;
}
.tool-btn:hover:not(:disabled) { border-color: var(--primary-color); color: var(--primary-color); }
.tool-btn.on { background: var(--primary-bg); border-color: var(--primary-color); color: var(--primary-color); }
.tool-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.shortcut-hint { font-size: 12px; color: var(--text-muted); margin-left: 6px; }
.shortcut-hint kbd {
  display: inline-block; padding: 1px 6px; font-size: 11px; font-family: monospace;
  background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 3px;
}

/* 代码编辑器（高亮叠加层） */
.code-editor {
  display: flex; border: 1px solid var(--border-color); border-radius: var(--border-radius);
  overflow: hidden; background: #1e1e2e;
}
.code-editor:focus-within { border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94,106,210,0.2); }
.gutter {
  padding: 10px 0; background: #181825; text-align: right; user-select: none;
  min-width: 36px; overflow: hidden; flex-shrink: 0;
}
.gutter div {
  padding: 0 9px; font-size: 13px; line-height: 20px; color: #6c7086;
  font-family: "Cascadia Code", "Fira Code", monospace;
}
.editor-stack { position: relative; flex: 1; }
.editor-highlight,
.editor-textarea {
  font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;
  font-size: 13px; line-height: 20px; padding: 10px 12px;
  white-space: pre-wrap; word-break: break-all; tab-size: 4;
}
.editor-highlight {
  position: absolute; inset: 0; margin: 0; overflow: hidden;
  color: #cdd6f4; pointer-events: none; background: transparent;
}
.editor-textarea {
  position: relative; width: 100%; height: 100%; display: block;
  border: none; outline: none; resize: none; overflow-y: auto;
  background: transparent; color: transparent; caret-color: #cdd6f4;
}
.editor-textarea::placeholder { color: #6c7086; }
.editor-textarea::selection { background: rgba(137,180,250,0.3); color: transparent; }
:deep(.tk-comment) { color: #6c7086; }
:deep(.tk-cmd) { color: #89b4fa; }
:deep(.tk-flag) { color: #f9e2af; }
:deep(.tk-str) { color: #a6e3a1; }
:deep(.tk-pipe) { color: #cba6f7; }
:deep(.tk-danger) { color: #f38ba8; font-weight: 700; background: rgba(243,139,168,0.15); border-radius: 3px; }

/* 危险命令警告条 */
.danger-banner {
  display: flex; align-items: center; gap: 8px; margin-top: 8px; padding: 7px 12px;
  background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;
  font-size: 12px; color: #b91c1c;
}
.danger-banner .d-cmd {
  font-family: "Cascadia Code", monospace; background: rgba(185,28,28,0.08);
  padding: 0 5px; border-radius: 3px; font-weight: 700;
}

/* 执行选项条 */
.exec-options {
  display: flex; align-items: center; gap: 16px; margin-top: 10px; padding: 9px 14px;
  background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px; flex-wrap: wrap;
}
.opt { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text-secondary); }
.opt-label { color: var(--text-muted); }
.opt-hint { font-size: 11px; color: var(--text-muted); }
.exec-buttons { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.selected-count { font-size: 13px; color: var(--text-muted); margin-right: 4px; }

/* ── 执行结果区 ── */
.result-section { flex: 1; display: flex; flex-direction: column; padding: 12px 20px; min-height: 0; }

/* 总览条 */
.summary-bar {
  display: flex; align-items: center; gap: 14px; padding: 10px 14px;
  background: var(--surface-color); border: 1px solid var(--border-color); border-radius: var(--border-radius);
  margin-bottom: 10px; flex-shrink: 0;
}
.sum-stat { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
.sum-stat .dot { width: 9px; height: 9px; border-radius: 50%; }
.sum-stat.success { color: #16a34a; } .sum-stat.success .dot { background: var(--success-color); }
.sum-stat.failed { color: var(--danger-color); } .sum-stat.failed .dot { background: var(--danger-color); }
.sum-stat.running { color: var(--primary-color); } .sum-stat.running .dot { background: var(--primary-color); animation: pulse 1.4s infinite; }
.sum-stat.pending { color: var(--text-muted); } .sum-stat.pending .dot { background: #d1d5db; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.progress-wrap { flex: 1; display: flex; align-items: center; gap: 10px; }
.progress-track { flex: 1; height: 7px; background: #eef0f4; border-radius: 4px; overflow: hidden; display: flex; }
.progress-fill-s { background: var(--success-color); height: 100%; transition: width 0.4s; }
.progress-fill-f { background: var(--danger-color); height: 100%; transition: width 0.4s; }
.progress-pct { font-size: 12px; color: var(--text-muted); font-family: "Cascadia Code", monospace; min-width: 76px; text-align: right; }
.btn-stop {
  display: inline-flex; align-items: center; gap: 5px; padding: 5px 14px; font-size: 12px; font-weight: 600;
  border: 1px solid #fecaca; border-radius: 6px; background: #fef2f2; color: var(--danger-color); cursor: pointer;
}
.btn-stop:hover:not(:disabled) { background: #fee2e2; }
.btn-stop:disabled { opacity: 0.5; cursor: not-allowed; }

/* 视图工具栏 */
.result-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-shrink: 0; }
.view-switch { display: flex; background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 7px; padding: 2px; gap: 2px; }
.view-tab {
  padding: 4px 14px; font-size: 12px; border: none; border-radius: 5px; cursor: pointer;
  background: transparent; color: var(--text-secondary); font-weight: 500;
}
.view-tab.active { background: var(--primary-color); color: #fff; }
.rt-spacer { flex: 1; }

/* 结果主体：列表 + 控制台 */
.result-body { display: flex; gap: 10px; flex: 1; min-height: 240px; }
.result-list {
  width: 200px; min-width: 200px; background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); overflow-y: auto; padding: 6px;
}
.rl-item {
  display: flex; align-items: center; gap: 7px; padding: 7px 9px; border-radius: 6px;
  cursor: pointer; font-size: 12.5px; transition: background 0.12s;
}
.rl-item:hover { background: var(--bg-color); }
.rl-item.active { background: var(--primary-bg); }
.rl-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.rl-dot.ok { background: var(--success-color); }
.rl-dot.err { background: var(--danger-color); }
.rl-dot.run { background: var(--primary-color); animation: pulse 1.4s infinite; }
.rl-dot.skip { background: #d1d5db; }
.rl-name { font-weight: 500; }
.rl-time { margin-left: auto; font-size: 11px; color: var(--text-muted); font-family: "Cascadia Code", monospace; }
.rl-item .retry {
  display: none; margin-left: auto; font-size: 10px; color: var(--primary-color);
  border: 1px solid var(--primary-color); border-radius: 4px; padding: 0 5px;
  line-height: 15px; background: var(--surface-color);
}
.rl-item.is-fail:hover .retry { display: inline-block; }
.rl-item.is-fail:hover .rl-time { display: none; }
.rl-group-label { font-size: 10.5px; font-weight: 700; color: var(--text-muted); padding: 8px 9px 3px; }

/* 控制台 */
.console-panel {
  flex: 1; display: flex; flex-direction: column; background: #1e1e2e;
  border-radius: var(--border-radius); overflow: hidden; min-width: 0;
}
.console-head {
  display: flex; align-items: center; gap: 10px; padding: 8px 14px;
  background: #181825; border-bottom: 1px solid #313244; flex-shrink: 0;
}
.ch-dot { width: 8px; height: 8px; border-radius: 50%; }
.ch-dot.ok { background: var(--success-color); }
.ch-dot.err { background: var(--danger-color); }
.ch-dot.run { background: var(--primary-color); animation: pulse 1.4s infinite; }
.ch-dot.skip { background: #6c7086; }
.ch-host { color: #cdd6f4; font-size: 12.5px; font-weight: 600; }
.ch-ip { color: #6c7086; font-size: 11.5px; font-family: "Cascadia Code", monospace; }
.ch-exit {
  font-size: 11px; font-family: "Cascadia Code", monospace; color: #f38ba8;
  background: rgba(243,139,168,0.12); padding: 1px 8px; border-radius: 4px;
}
.ch-exit.ok { color: #a6e3a1; background: rgba(166,227,161,0.12); }
.ch-exit.skipped { color: #6c7086; background: rgba(108,112,134,0.15); }
.ch-actions { margin-left: auto; display: flex; gap: 6px; }
.ch-btn {
  font-size: 11px; color: #a6adc8; background: transparent; border: 1px solid #45475a;
  border-radius: 4px; padding: 2px 9px; cursor: pointer;
}
.ch-btn:hover { color: #cdd6f4; border-color: #6c7086; }
.console-body {
  flex: 1; padding: 12px 16px; font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;
  font-size: 12.5px; line-height: 1.65; color: #cdd6f4; overflow: auto;
  white-space: pre-wrap; word-break: break-all;
}
:deep(.t-hl) { background: rgba(249,226,175,0.25); color: #f9e2af; border-radius: 2px; padding: 0 1px; }

/* 聚合视图 */
.agg-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; min-height: 240px; }
.agg-section { background: #1e1e2e; border-radius: var(--border-radius); overflow: hidden; flex-shrink: 0; }
.agg-head {
  display: flex; align-items: center; gap: 10px; padding: 8px 14px;
  background: #181825; border-bottom: 1px solid #313244; cursor: pointer;
}
.agg-head:hover { background: #1f1f30; }
.agg-section .console-body { max-height: 260px; flex: none; }

/* 对比视图 */
.compare-body { flex: 1; display: flex; flex-direction: column; min-height: 240px; }
.compare-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-shrink: 0; }
.compare-vs { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.compare-hint { font-size: 12px; color: var(--warning-color); margin-left: 8px; }
.compare-table-wrap {
  flex: 1; overflow: auto; background: #1e1e2e; border-radius: var(--border-radius);
}
.compare-table { width: 100%; border-collapse: collapse; font-family: "Cascadia Code", monospace; font-size: 12.5px; }
.compare-table td { padding: 2px 12px; color: #cdd6f4; vertical-align: top; white-space: pre-wrap; word-break: break-all; }
.compare-table .ln {
  width: 40px; text-align: right; color: #6c7086; user-select: none;
  border-right: 1px solid #313244; background: #181825; white-space: nowrap;
}
.compare-table .cc { width: calc(50% - 20px); }
.compare-table tr.diff .cc { background: rgba(249,226,175,0.08); color: #f9e2af; }
.compare-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); font-size: 13px;
}

/* 空状态 */
.output-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--text-muted); gap: 8px;
}
.output-empty .empty-icon { font-size: 40px; opacity: 0.4; }
.output-empty p { font-size: 14px; }

/* ── 状态栏 ── */
.status-bar {
  display: flex; align-items: center; gap: 20px; padding: 8px 20px;
  background: var(--surface-color); border-top: 1px solid var(--border-color);
  font-size: 12px; color: var(--text-secondary); flex-shrink: 0;
}
.sb-stat b { font-family: "Cascadia Code", monospace; font-weight: 600; }
.sb-stat b.ok { color: #16a34a; }
.sb-stat b.err { color: var(--danger-color); }
.sb-right { margin-left: auto; color: var(--warning-color); font-size: 12px; }

/* ── 历史抽屉 ── */
.history-drawer {
  position: absolute; top: 0; right: 0; bottom: 0; width: 520px; max-width: 90%;
  background: var(--surface-color); border-left: 1px solid var(--border-color);
  box-shadow: -12px 0 40px rgba(0,0,0,0.12); display: none; flex-direction: column; z-index: 50;
}
.history-drawer.show { display: flex; }
.hd-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid var(--border-color); flex-shrink: 0;
}
.hd-header h4 { font-size: 14px; font-weight: 700; }
.hd-close { background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text-muted); }
.hd-filters {
  display: flex; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--border-color); flex-shrink: 0;
}
.hd-list { flex: 1; overflow-y: auto; padding: 10px 14px; }
.hd-item {
  border: 1px solid var(--border-color); border-radius: var(--border-radius);
  padding: 10px 13px; margin-bottom: 8px; transition: border-color 0.15s;
}
.hd-item:hover { border-color: var(--primary-color); }
.hd-cmd { font-family: "Cascadia Code", monospace; font-size: 12px; margin-bottom: 6px; word-break: break-all; }
.hd-meta { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-muted); flex-wrap: wrap; }
.hd-tag { padding: 1px 7px; border-radius: 4px; font-weight: 600; }
.hd-tag.ok { background: #f0fdf4; color: #16a34a; }
.hd-tag.warn { background: #fffbeb; color: #b45309; }
.hd-acts { margin-left: auto; display: flex; gap: 5px; }
.hd-act {
  font-size: 11px; padding: 2px 9px; border-radius: 4px; border: 1px solid var(--border-color);
  background: var(--surface-color); color: var(--text-secondary); cursor: pointer;
}
.hd-act:hover { border-color: var(--primary-color); color: var(--primary-color); }
.hd-act.retry-fail { color: var(--danger-color); }
.hd-act.retry-fail:hover { border-color: var(--danger-color); }
.hd-empty { padding: 30px; text-align: center; color: var(--text-muted); font-size: 13px; }
.hd-pagination { display: flex; justify-content: flex-end; padding: 8px 14px; border-top: 1px solid var(--border-color); flex-shrink: 0; }
</style>
