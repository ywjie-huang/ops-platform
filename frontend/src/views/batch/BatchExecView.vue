<template>
  <div>
    <div class="page-header"><h2 class="page-title">批量执行</h2></div>

    <el-tabs v-model="activeTab">
      <!-- 执行 Tab -->
      <el-tab-pane label="执行命令" name="exec">
        <el-row :gutter="16">
          <!-- 左侧：选主机 + 命令 -->
          <el-col :span="10">
            <div class="data-card" style="margin-bottom:16px">
              <h4 style="margin:0 0 12px">选择主机</h4>
              <el-input v-model="assetSearch" placeholder="搜索主机…" clearable style="margin-bottom:8px" />
              <el-table
                ref="assetTableRef"
                :data="filteredAssets"
                stripe
                size="small"
                max-height="360"
                @selection-change="handleSelectionChange"
              >
                <el-table-column type="selection" width="40" />
                <el-table-column prop="name" label="名称" min-width="100" />
                <el-table-column prop="ip_address" label="IP" width="130" />
                <el-table-column prop="status" label="状态" width="70">
                  <template #default="{row}">
                    <el-tag :type="row.status === '使用中' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
              <div style="margin-top:8px;font-size:13px;color:var(--text-muted)">
                已选 <strong>{{ selectedAssets.length }}</strong> 台主机
              </div>
            </div>

            <div class="data-card">
              <h4 style="margin:0 0 12px">执行命令</h4>
              <el-input
                v-model="command"
                type="textarea"
                :rows="4"
                placeholder="输入要执行的命令，例：uptime&#10;df -h&#10;systemctl status nginx"
              />
              <div style="margin-top:12px;display:flex;gap:8px">
                <el-button type="primary" :loading="executing" :disabled="!selectedAssets.length || !command" @click="handleExecute">
                  执行
                </el-button>
                <el-button @click="handleClear" :disabled="executing">清空</el-button>
                <span style="margin-left:auto;line-height:32px;font-size:13px;color:var(--text-muted)">
                  超时 30 秒
                </span>
              </div>
            </div>
          </el-col>

          <!-- 右侧：输出 -->
          <el-col :span="14">
            <div class="data-card output-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <h4 style="margin:0">执行结果</h4>
                <el-tag v-if="execSummary" :type="execSummary.failed > 0 ? 'warning' : 'success'" size="small">
                  成功 {{ execSummary.success }} / 失败 {{ execSummary.failed }} / 共 {{ execSummary.total }}
                </el-tag>
              </div>

              <div v-if="!outputs.length" class="empty-output">
                选择主机并输入命令，点击执行查看结果
              </div>

              <div v-else class="output-list">
                <div v-for="item in outputs" :key="item.host_id" class="output-item">
                  <div class="output-header">
                    <span class="output-host">
                      <el-icon><Monitor /></el-icon>
                      {{ item.host_name }} ({{ item.host_ip }})
                    </span>
                    <el-tag v-if="item.done" :type="item.exit_code === 0 ? 'success' : 'danger'" size="small">
                      {{ item.exit_code === 0 ? '成功' : `失败 (${item.exit_code})` }}
                    </el-tag>
                    <el-tag v-else type="info" size="small">执行中…</el-tag>
                  </div>
                  <pre class="output-content" v-text="item.content || '(无输出)'" />
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 历史 Tab -->
      <el-tab-pane label="执行历史" name="history">
        <div class="data-card">
          <div class="filter-bar">
            <el-input v-model="historyFilters.keyword" placeholder="搜索命令或主机…" clearable style="width:240px" @keyup.enter="fetchHistory" />
            <el-select v-model="historyFilters.status" placeholder="状态" clearable style="width:120px" @change="fetchHistory">
              <el-option label="已完成" value="completed" />
              <el-option label="有失败" value="failed" />
            </el-select>
            <el-button @click="fetchHistory">筛选</el-button>
          </div>

          <el-table :data="historyItems" stripe v-loading="historyLoading">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="command" label="命令" min-width="250" show-overflow-tooltip />
            <el-table-column prop="asset_names" label="执行主机" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{row}">
                <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                  {{ row.status === 'completed' ? '已完成' : '有失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="结果" width="120" align="center">
              <template #default="{row}">
                <span style="color:var(--el-color-success)">{{ row.success_hosts }}</span> /
                <span style="color:var(--el-color-danger)">{{ row.failed_hosts }}</span> /
                {{ row.total_hosts }}
              </template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="80" />
            <el-table-column prop="created_at" label="执行时间" width="170" />
            <el-table-column label="操作" width="80">
              <template #default="{row}">
                <el-button link type="danger" size="small" @click="handleDeleteHistory(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="historyPage"
              v-model:page-size="historyPageSize"
              :page-sizes="[10, 20, 50]"
              :total="historyTotal"
              layout="total, sizes, prev, pager, next"
              @current-change="fetchHistory"
              @size-change="fetchHistory"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import { getExecHistory, deleteExecHistory } from '@/api/batch_exec'
import { getAssets } from '@/api/assets'
import { getToken } from '@/utils/auth'

const activeTab = ref('exec')

// ─── 主机选择 ──────────────────────────────────────────────
const allAssets = ref<any[]>([])
const selectedAssets = ref<any[]>([])
const assetSearch = ref('')

const filteredAssets = computed(() => {
  if (!assetSearch.value) return allAssets.value
  const kw = assetSearch.value.toLowerCase()
  return allAssets.value.filter(a =>
    a.name.toLowerCase().includes(kw) || a.ip_address.includes(kw)
  )
})

function handleSelectionChange(rows: any[]) {
  selectedAssets.value = rows
}

// ─── 执行 ──────────────────────────────────────────────────
const command = ref('')
const executing = ref(false)
const outputs = ref<any[]>([])
const execSummary = ref<any>(null)

function handleClear() {
  command.value = ''
  outputs.value = []
  execSummary.value = null
}

async function handleExecute() {
  if (!selectedAssets.value.length || !command.value) return

  executing.value = true
  outputs.value = []
  execSummary.value = null

  const assetIds = selectedAssets.value.map(a => a.id)

  // WebSocket URL
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${location.host}/api/v1/batch-exec/ws/exec`
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    ws.send(JSON.stringify({
      asset_ids: assetIds,
      command: command.value,
      timeout: 30,
    }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      if (data.type === 'exec_begin') {
        // 初始化每台主机的输出区
        outputs.value = data.hosts.map((h: any) => ({
          host_id: h.id,
          host_name: h.name,
          host_ip: h.ip,
          content: '',
          done: false,
          exit_code: 0,
        }))
      } else if (data.type === 'exec_result') {
        // 追加输出
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
        executing.value = false
        ElMessage.success(`执行完成：成功 ${data.success}，失败 ${data.failed}`)
        // 刷新历史
        fetchHistory()
      } else if (data.type === 'error') {
        ElMessage.error(data.message)
        executing.value = false
      }
    } catch (e) {
      console.error('WebSocket message parse error:', e)
    }
  }

  ws.onerror = () => {
    ElMessage.error('WebSocket 连接失败')
    executing.value = false
  }

  ws.onclose = () => {
    if (executing.value) {
      executing.value = false
    }
  }
}

// ─── 历史 ──────────────────────────────────────────────────
const historyItems = ref<any[]>([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)
const historyFilters = reactive({ keyword: '', status: '' })

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res: any = await getExecHistory({
      ...historyFilters,
      page: historyPage.value,
      page_size: historyPageSize.value,
    })
    historyItems.value = res.data.items
    historyTotal.value = res.data.total
  } finally { historyLoading.value = false }
}

async function handleDeleteHistory(row: any) {
  await ElMessageBox.confirm(`确定删除执行记录 #${row.id}？`, '删除确认', { type: 'warning' })
  await deleteExecHistory(row.id)
  ElMessage.success('删除成功')
  fetchHistory()
}

// ─── 初始化 ────────────────────────────────────────────────
async function fetchAssets() {
  try {
    const res: any = await getAssets({ page: 1, page_size: 1000 })
    allAssets.value = res.data.items.filter((a: any) => a.status === '使用中')
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

onMounted(() => { fetchAssets(); fetchHistory() })
</script>

<style scoped>
.output-card { min-height: 500px; }
.empty-output {
  display: flex; align-items: center; justify-content: center;
  height: 300px; color: var(--text-muted); font-size: 14px;
  border: 1px dashed var(--border-color); border-radius: 8px;
}
.output-list { display: flex; flex-direction: column; gap: 12px; }
.output-item { border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
.output-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #f5f7fa; border-bottom: 1px solid var(--border-color);
}
.output-host { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; }
.output-content {
  margin: 0; padding: 12px; font-size: 13px; font-family: 'Cascadia Code', 'Fira Code', monospace;
  background: #1e1e2e; color: #cdd6f4; max-height: 300px; overflow: auto;
  white-space: pre-wrap; word-break: break-all; line-height: 1.5;
}
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
