<template>
  <div>
    <div class="detail-header">
      <div>
        <div class="detail-title-row">
          <el-button text aria-label="返回 Docker 监控列表" @click="$router.push('/assets/docker')">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h2 class="page-title">{{ host.name || '主机详情' }}</h2>
          <el-tag :type="host.online ? 'success' : 'danger'" size="small">
            <span class="tag-dot" :class="host.online ? 'dot-success' : 'dot-danger'" aria-hidden="true"></span>
            {{ host.online ? '在线' : '离线' }}
          </el-tag>
          <el-tag v-if="containerSummary.abnormal > 0" type="warning" size="small">
            {{ containerSummary.abnormal }} 个异常容器
          </el-tag>
        </div>
        <div class="detail-fields">
          <div>
            <div class="field-label">Agent 地址</div>
            <div class="field-value mono">{{ host.endpoint || '-' }}</div>
          </div>
          <div>
            <div class="field-label">主机 IP</div>
            <div class="field-value mono">{{ host.host_ip || endpointHost(host.endpoint) || '-' }}</div>
          </div>
          <div>
            <div class="field-label">Docker 版本</div>
            <div class="field-value">{{ host.docker_version || '-' }}</div>
          </div>
          <div>
            <div class="field-label">最后同步</div>
            <div class="field-value" :class="syncValueClass">{{ relativeSyncTime }}</div>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 15s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" size="small" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
        <el-button :loading="refreshing" type="primary" size="small" aria-label="立即刷新 Docker 主机数据" @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          立即刷新
        </el-button>
        <el-button type="danger" plain size="small" :aria-label="`删除主机 ${host.name}`" @click="handleDelete">删除主机</el-button>
      </div>
    </div>

    <div class="sync-notice" :class="syncNoticeClass">
      <span class="status-dot" :class="syncDotClass" aria-hidden="true"></span>
      <span>{{ syncNoticeText }}</span>
    </div>

    <div class="summary-grid" role="region" aria-label="主机指标概览">
      <div v-for="item in overviewCards" :key="item.label" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value" :class="item.valueClass">{{ item.value }}</div>
        <el-progress
          v-if="item.percent != null"
          :percentage="Math.min(item.percent, 100)"
          :stroke-width="4"
          :show-text="false"
          :color="progressColor(item.percent)"
          class="stat-progress"
        />
        <div class="metric-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="panel">
        <div class="panel-head">
          <div>
            <h3 class="panel-title">容器列表</h3>
            <p class="panel-subtitle">异常和重启次数较高的容器优先展示。</p>
          </div>
          <div class="container-tools">
            <el-input v-model="keyword" placeholder="搜索容器名或镜像" clearable class="search-input" aria-label="搜索容器" />
            <el-button size="small" :loading="loading" @click="fetchContainers">刷新列表</el-button>
          </div>
        </div>

        <div class="status-tabs" role="tablist" aria-label="容器状态筛选">
          <button
            v-for="tab in statusTabs"
            :key="tab.value"
            type="button"
            class="status-tab"
            :class="{ active: statusFilter === tab.value }"
            @click="statusFilter = tab.value"
          >
            {{ tab.label }} {{ tab.count }}
          </button>
        </div>

        <div class="table-wrapper">
          <el-table :data="pagedContainers" stripe v-loading="loading">
            <el-table-column prop="name" label="容器" min-width="210" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="container-name">
                  <strong>{{ row.name }}</strong>
                  <span class="mono">{{ row.image }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="containerStatusType(row.status)" size="small">
                  <span class="tag-dot" :class="containerDotClass(row.status)" aria-hidden="true"></span>
                  {{ containerStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="CPU" width="100" align="center">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.cpu_percent > THRESHOLD_WARN, 'text-danger': row.cpu_percent > THRESHOLD_DANGER }">
                  {{ Number(row.cpu_percent || 0).toFixed(1) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="内存" width="170">
              <template #default="{ row }">
                <div class="memory-cell">
                  <el-progress
                    :percentage="Math.min(row.memory_percent || 0, 100)"
                    :stroke-width="6"
                    :show-text="false"
                    :color="progressColor(row.memory_percent || 0)"
                    class="memory-progress"
                  />
                  <span class="mono memory-text">{{ formatBytes(row.memory_usage) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="端口" min-width="190" show-overflow-tooltip>
              <template #default="{ row }">{{ formatPorts(row.ports) }}</template>
            </el-table-column>
            <el-table-column prop="restart_count" label="重启" width="80" align="center">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.restart_count > 3, 'text-danger': row.restart_count > 10 }">{{ row.restart_count }}</span>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="150">
              <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right" align="right">
              <template #default="{ row }">
                <div class="action-cell">
                  <el-button
                    size="small"
                    type="info"
                    link
                    :aria-label="`查看容器 ${row.name} 详情`"
                    @click.stop="openContainerInspect(row)"
                  >详情</el-button>
                  <el-button
                    size="small"
                    type="info"
                    link
                    :aria-label="`查看容器 ${row.name} 日志`"
                    @click.stop="openContainerLogs(row)"
                  >日志</el-button>
                  <el-button
                    v-if="row.status !== 'running'"
                    size="small"
                    type="success"
                    link
                    :aria-label="`启动容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'start')"
                  >启动</el-button>
                  <el-button
                    v-if="row.status === 'running'"
                    size="small"
                    type="primary"
                    link
                    :aria-label="`重启容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'restart')"
                  >重启</el-button>
                  <el-button
                    v-if="row.status === 'running'"
                    size="small"
                    type="warning"
                    link
                    :aria-label="`停止容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'stop')"
                  >停止</el-button>
                  <el-button
                    size="small"
                    type="danger"
                    link
                    :aria-label="`删除容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'delete')"
                  >删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredContainers.length"
            layout="total, sizes, prev, pager, next"
            small
          />
        </div>
      </div>

      <aside class="panel health-panel">
        <div class="panel-head compact">
          <h3 class="panel-title">主机健康</h3>
          <el-tag :type="healthTagType" size="small">{{ healthLabel }}</el-tag>
        </div>
        <div class="health-list">
          <div v-for="item in healthItems" :key="item.label" class="health-item">
            <div class="health-row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="health-bar" aria-hidden="true">
              <span :class="item.barClass" :style="{ width: item.percent + '%' }"></span>
            </div>
          </div>
        </div>
        <div class="event-list">
          <div class="event-item">
            <strong>异常容器</strong>
            <span>{{ containerSummary.abnormal > 0 ? `发现 ${containerSummary.abnormal} 个异常容器` : '未发现异常容器' }}</span>
          </div>
          <div class="event-item">
            <strong>同步状态</strong>
            <span>{{ syncHintText }}</span>
          </div>
          <div class="event-item">
            <strong>建议动作</strong>
            <span>{{ actionSuggestion }}</span>
          </div>
        </div>
      </aside>
    </div>

    <el-drawer v-model="logsDrawerVisible" size="720px" :with-header="false" destroy-on-close>
      <div class="drawer-head">
        <div class="drawer-head-copy">
          <h3>{{ selectedContainer?.name || '容器' }}</h3>
          <div class="drawer-sub">{{ selectedContainer?.image || '-' }} · {{ selectedContainer ? containerStatusLabel(selectedContainer.status) : '' }}</div>
        </div>
        <div class="drawer-actions">
          <el-button size="small" :loading="logsLoading" @click="fetchSelectedContainerLogs">刷新</el-button>
          <el-button size="small" :disabled="!displayedContainerLogs" @click="copyLogs">复制</el-button>
          <el-button size="small" :disabled="!displayedContainerLogs" @click="downloadLogs">下载</el-button>
        </div>
      </div>
      <div class="drawer-body">
        <div class="log-toolbar">
          <el-radio-group v-model="logMode" size="small" @change="fetchSelectedContainerLogs">
            <el-radio-button value="lines">按行数</el-radio-button>
            <el-radio-button value="time">按时间段</el-radio-button>
          </el-radio-group>
          <el-select
            v-if="logMode === 'lines'"
            v-model="logTailLines"
            size="small"
            class="log-tail-select"
            @change="fetchSelectedContainerLogs"
          >
            <el-option :value="100" label="100 行" />
            <el-option :value="300" label="300 行" />
            <el-option :value="500" label="500 行" />
            <el-option :value="1000" label="1000 行" />
          </el-select>
          <el-select
            v-else
            v-model="logTimeWindow"
            size="small"
            class="log-tail-select"
            @change="fetchSelectedContainerLogs"
          >
            <el-option :value="300" label="近 5 分钟" />
            <el-option :value="900" label="近 15 分钟" />
            <el-option :value="1800" label="近 30 分钟" />
            <el-option :value="3600" label="近 1 小时" />
            <el-option :value="0" label="全部" />
          </el-select>
          <el-input
            v-model="logKeyword"
            size="small"
            clearable
            class="log-keyword-input"
            placeholder="筛选关键字"
            :prefix-icon="Search"
            aria-label="筛选 Docker 容器日志关键字"
          />
          <span class="log-count" v-if="logCountLabel">{{ logCountLabel }}</span>
          <span class="log-live" :class="{ 'is-live': liveActive }" role="status" :aria-label="liveActive ? '实时日志跟随中' : '实时连接已断开'">
            <i class="live-dot" aria-hidden="true"></i>
            {{ liveActive ? '实时中' : '已断开' }}
          </span>
        </div>
        <div class="log-scroll" v-loading="logsLoading">
          <pre ref="logScrollRef" class="log-box" tabindex="0" role="log" :aria-label="normalizedLogKeyword ? '筛选并高亮后的 Docker 容器日志' : 'Docker 容器日志'"><LogHighlightedText
            v-if="normalizedLogKeyword && displayedContainerLogs"
            :lines="highlightedContainerLogLines"
          /><template v-else>{{ logDisplayText }}</template></pre>
        </div>
      </div>
    </el-drawer>

    <el-drawer v-model="inspectDrawerVisible" size="760px" :with-header="false" destroy-on-close>
      <div class="drawer-head">
        <div class="drawer-head-copy">
          <h3>{{ inspectContainer?.name || '容器详情' }}</h3>
          <div class="drawer-sub">
            <span class="mono">{{ inspectContainer?.image || '-' }}</span>
            <template v-if="inspectContainer"> · {{ containerStatusLabel(inspectContainer.status) }}</template>
          </div>
        </div>
        <div class="drawer-actions">
          <el-button size="small" :loading="inspectLoading" @click="fetchContainerInspect">刷新</el-button>
        </div>
      </div>
      <div class="drawer-body inspect-body" v-loading="inspectLoading">
        <template v-if="inspectData">
          <section class="inspect-section">
            <h4 class="inspect-section-title">基本信息</h4>
            <dl class="inspect-grid">
              <div class="inspect-field inspect-field-wide"><dt>完整 ID</dt><dd class="mono break-all">{{ inspectData.Id || '-' }}</dd></div>
              <div class="inspect-field"><dt>创建时间</dt><dd>{{ formatInspectTime(inspectData.Created) }}</dd></div>
              <div class="inspect-field"><dt>启动时间</dt><dd>{{ formatInspectTime(inspectState.StartedAt) }}</dd></div>
              <div class="inspect-field"><dt>PID</dt><dd class="mono">{{ inspectState.Pid ?? '-' }}</dd></div>
              <div class="inspect-field"><dt>退出码</dt><dd class="mono" :class="{ 'text-danger': Number(inspectState.ExitCode) > 0 }">{{ inspectState.ExitCode ?? '-' }}</dd></div>
              <div class="inspect-field"><dt>重启策略</dt><dd>{{ restartPolicyText }}</dd></div>
            </dl>
          </section>

          <section class="inspect-section">
            <h4 class="inspect-section-title">运行配置</h4>
            <dl class="inspect-grid">
              <div class="inspect-field inspect-field-wide"><dt>启动命令 Cmd</dt><dd class="mono break-all">{{ cmdText }}</dd></div>
              <div class="inspect-field inspect-field-wide"><dt>入口 Entrypoint</dt><dd class="mono break-all">{{ entrypointText }}</dd></div>
              <div class="inspect-field"><dt>工作目录</dt><dd class="mono">{{ inspectConfig.WorkingDir || '/' }}</dd></div>
              <div class="inspect-field"><dt>运行用户</dt><dd class="mono">{{ inspectConfig.User || 'root' }}</dd></div>
              <div class="inspect-field"><dt>TTY</dt><dd>{{ inspectConfig.Tty ? '是' : '否' }}</dd></div>
            </dl>
          </section>

          <section class="inspect-section collapsible">
            <header class="inspect-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.env" @click="toggleSection('env')" @keyup.enter="toggleSection('env')">
              <h4 class="inspect-section-title">环境变量</h4>
              <span class="inspect-section-summary">{{ envItems.length }} 项</span>
              <el-icon class="inspect-caret" :class="{ open: !sectionCollapse.env }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.env" class="inspect-section-body">
              <ul class="kv-list">
                <li v-for="item in envItems" :key="item.key" class="kv-item">
                  <span class="kv-key mono break-all">{{ item.key }}</span>
                  <span class="kv-value mono break-all" :class="{ masked: item.sensitive && !revealedEnvKeys.has(item.key) }">{{ envDisplayValue(item) }}</span>
                  <el-button v-if="item.sensitive" link size="small" class="kv-reveal" :aria-label="revealedEnvKeys.has(item.key) ? `隐藏 ${item.key} 值` : `显示 ${item.key} 值`" @click="toggleEnvReveal(item.key)">{{ revealedEnvKeys.has(item.key) ? '隐藏' : '显示' }}</el-button>
                </li>
                <li v-if="!envItems.length" class="kv-empty">无环境变量</li>
              </ul>
            </div>
          </section>

          <section class="inspect-section collapsible">
            <header class="inspect-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.network" @click="toggleSection('network')" @keyup.enter="toggleSection('network')">
              <h4 class="inspect-section-title">网络</h4>
              <span class="inspect-section-summary">{{ networkSummary }}</span>
              <el-icon class="inspect-caret" :class="{ open: !sectionCollapse.network }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.network" class="inspect-section-body">
              <dl class="inspect-grid">
                <div class="inspect-field"><dt>IP 地址</dt><dd class="mono">{{ inspectNetwork.IPAddress || '-' }}</dd></div>
                <div class="inspect-field"><dt>网络模式</dt><dd class="mono">{{ inspectHostConfig.NetworkMode || '-' }}</dd></div>
                <div class="inspect-field"><dt>MAC 地址</dt><dd class="mono">{{ inspectNetwork.MacAddress || '-' }}</dd></div>
              </dl>
              <div v-if="portBindingsText !== '-'" class="inspect-sub">
                <div class="inspect-sub-title">端口映射</div>
                <div class="mono break-all">{{ portBindingsText }}</div>
              </div>
              <div v-if="linkedNetworks.length" class="inspect-sub">
                <div class="inspect-sub-title">连接的网络</div>
                <div v-for="n in linkedNetworks" :key="n.name" class="mono">
                  {{ n.name }}<template v-if="n.ip"> · {{ n.ip }}</template>
                </div>
              </div>
            </div>
          </section>

          <section class="inspect-section collapsible">
            <header class="inspect-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.mounts" @click="toggleSection('mounts')" @keyup.enter="toggleSection('mounts')">
              <h4 class="inspect-section-title">挂载</h4>
              <span class="inspect-section-summary">{{ inspectMounts.length }} 项</span>
              <el-icon class="inspect-caret" :class="{ open: !sectionCollapse.mounts }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.mounts" class="inspect-section-body">
              <ul class="kv-list">
                <li v-for="(m, i) in inspectMounts" :key="i" class="kv-item kv-item-block">
                  <span class="mono break-all">{{ m.Source || m.Name }} <span class="kv-arrow">→</span> {{ m.Destination }}</span>
                  <el-tag size="small" type="info">{{ m.Type || 'bind' }}{{ m.RW === false ? ' · 只读' : '' }}</el-tag>
                </li>
                <li v-if="!inspectMounts.length" class="kv-empty">无挂载</li>
              </ul>
            </div>
          </section>

          <section class="inspect-section collapsible">
            <header class="inspect-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.health" @click="toggleSection('health')" @keyup.enter="toggleSection('health')">
              <h4 class="inspect-section-title">健康检查</h4>
              <span class="inspect-section-summary">{{ healthSummary }}</span>
              <el-icon class="inspect-caret" :class="{ open: !sectionCollapse.health }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.health" class="inspect-section-body">
              <template v-if="inspectConfig.Healthcheck || inspectState.Health">
                <dl class="inspect-grid">
                  <div v-if="inspectState.Health" class="inspect-field">
                    <dt>当前状态</dt><dd><el-tag :type="inspectHealthTagType" size="small">{{ healthStatusLabel }}</el-tag></dd>
                  </div>
                  <div v-if="inspectState.Health" class="inspect-field"><dt>连续失败</dt><dd class="mono">{{ inspectState.Health.FailingStreak }}</dd></div>
                  <div class="inspect-field inspect-field-wide"><dt>探针命令</dt><dd class="mono break-all">{{ healthcheckTestText }}</dd></div>
                  <div class="inspect-field"><dt>间隔</dt><dd class="mono">{{ healthcheckIntervalText }}</dd></div>
                  <div class="inspect-field"><dt>超时</dt><dd class="mono">{{ healthcheckTimeoutText }}</dd></div>
                  <div class="inspect-field"><dt>重试次数</dt><dd class="mono">{{ inspectConfig.Healthcheck?.Retries ?? '-' }}</dd></div>
                </dl>
              </template>
              <div v-else class="kv-empty">未配置健康检查</div>
            </div>
          </section>

          <section class="inspect-section collapsible">
            <header class="inspect-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.resources" @click="toggleSection('resources')" @keyup.enter="toggleSection('resources')">
              <h4 class="inspect-section-title">资源限制</h4>
              <span class="inspect-section-summary">{{ resourcesSummary }}</span>
              <el-icon class="inspect-caret" :class="{ open: !sectionCollapse.resources }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.resources" class="inspect-section-body">
              <dl class="inspect-grid">
                <div class="inspect-field"><dt>内存限制</dt><dd>{{ inspectHostConfig.Memory ? formatBytes(inspectHostConfig.Memory) : '未限制' }}</dd></div>
                <div class="inspect-field"><dt>CPU 限制</dt><dd>{{ cpuLimitText }}</dd></div>
                <div class="inspect-field"><dt>CPU 权重</dt><dd class="mono">{{ inspectHostConfig.CpuShares || '-' }}</dd></div>
                <div class="inspect-field"><dt>PID 限制</dt><dd class="mono">{{ (inspectHostConfig.PidsLimit ?? 0) > 0 ? inspectHostConfig.PidsLimit : '未限制' }}</dd></div>
                <div class="inspect-field"><dt>OOM 禁杀</dt><dd>{{ inspectHostConfig.OomKillDisable ? '是' : '否' }}</dd></div>
              </dl>
            </div>
          </section>

          <section class="inspect-section collapsible">
            <header class="inspect-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.labels" @click="toggleSection('labels')" @keyup.enter="toggleSection('labels')">
              <h4 class="inspect-section-title">标签</h4>
              <span class="inspect-section-summary">{{ labelEntries.length }} 项</span>
              <el-icon class="inspect-caret" :class="{ open: !sectionCollapse.labels }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.labels" class="inspect-section-body">
              <ul class="kv-list">
                <li v-for="item in labelEntries" :key="item.key" class="kv-item">
                  <span class="kv-key mono break-all">{{ item.key }}</span>
                  <span class="kv-value mono break-all">{{ item.value || '(空)' }}</span>
                </li>
                <li v-if="!labelEntries.length" class="kv-empty">无标签</li>
              </ul>
            </div>
          </section>
        </template>
        <el-empty v-else-if="!inspectLoading" description="暂无详情数据" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onActivated, onDeactivated, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowDown, Refresh, Search } from '@element-plus/icons-vue'
import LogHighlightedText from '@/components/LogHighlightedText'
import {
  getDockerHost,
  deleteDockerHost,
  refreshDockerHost,
  getHostContainers,
  getDockerContainerLogs,
  getDockerContainerInspect,
  buildDockerLogStreamUrl,
  startDockerContainer,
  stopDockerContainer,
  restartDockerContainer,
  deleteDockerContainer,
} from '@/api/containers'
import { getHostSyncState, secondsSince, sortContainersByRisk, summarizeContainers } from '@/utils/dockerMonitor'
import { filterLogLines, highlightLogLines, normalizeLogKeyword } from '@/utils/logSearch'

const THRESHOLD_WARN = 70
const THRESHOLD_DANGER = 85

const route = useRoute()
const router = useRouter()
const hostName = computed(() => (
  route.name === 'DockerDetail' ? String(route.params.name ?? '') : ''
))

const host = ref<any>({})
const containers = ref<any[]>([])
const loading = ref(false)
const refreshing = ref(false)
const keyword = ref('')
const statusFilter = ref('all')
const page = ref(1)
const pageSize = ref(20)
const autoRefresh = ref(false)
const selectedContainer = ref<any | null>(null)
const logsDrawerVisible = ref(false)
const logsLoading = ref(false)
const containerLogs = ref('')
const logKeyword = ref('')
const logMode = ref<'lines' | 'time'>('lines')
const logTailLines = ref(300)
const logTimeWindow = ref(900) // 近 15 分钟
const liveActive = ref(false)
const logScrollRef = ref<HTMLElement | null>(null)
// 实时跟随保留的最大行数，避免 DOM 无限增长
const LIVE_LOG_MAX_LINES = 5000
let logEs: EventSource | null = null
let liveSince = 0

// 实际返回的日志行数：用于在工具栏展示
const logLineCount = computed(() => {
  const text = containerLogs.value.trim()
  return text ? text.split('\n').length : 0
})
const normalizedLogKeyword = computed(() => normalizeLogKeyword(logKeyword.value))
const displayedContainerLogs = computed(() => {
  return filterLogLines(containerLogs.value, normalizedLogKeyword.value)
})
const highlightedContainerLogLines = computed(() => {
  return highlightLogLines(displayedContainerLogs.value, normalizedLogKeyword.value)
})
const displayedLogLineCount = computed(() => {
  const text = displayedContainerLogs.value.trim()
  return text ? text.split('\n').length : 0
})
const logDisplayText = computed(() => {
  if (displayedContainerLogs.value) return displayedContainerLogs.value
  return containerLogs.value && normalizedLogKeyword.value ? '未找到匹配日志' : '暂无日志'
})
const logCountLabel = computed(() => {
  if (logsLoading.value || !containerLogs.value) return ''
  if (normalizedLogKeyword.value) return `匹配 ${displayedLogLineCount.value} / ${logLineCount.value} 行`
  return `共 ${logLineCount.value} 行`
})

let refreshTimer: ReturnType<typeof setInterval> | null = null

const containerSummary = computed(() => summarizeContainers(containers.value))
const syncState = computed(() => getHostSyncState(host.value))
const relativeSyncTime = computed(() => formatRelativeTime(host.value.last_heartbeat))

const syncValueClass = computed(() => {
  if (syncState.value === 'fresh') return ''
  if (syncState.value === 'stale') return 'text-warning'
  return 'text-danger'
})

const syncNoticeClass = computed(() => syncState.value === 'fresh' ? 'notice-info' : syncState.value === 'stale' ? 'notice-warning' : 'notice-danger')
const syncDotClass = computed(() => syncState.value === 'fresh' ? 'dot-info' : syncState.value === 'stale' ? 'dot-warning' : 'dot-danger')
const syncHintText = computed(() => {
  if (syncState.value === 'fresh') return 'Agent 同步正常'
  if (syncState.value === 'stale') return '数据可能过期'
  if (syncState.value === 'offline') return host.value.status_message || 'Agent 连接失败'
  return '等待首次同步'
})
const syncNoticeText = computed(() => {
  if (syncState.value === 'fresh') return '当前容器数据来自平台最近一次 Agent 同步。需要现场确认时，请点击“立即刷新”。'
  if (syncState.value === 'stale') return '当前数据超过 60 秒未同步，建议立即刷新后再执行容器操作。'
  return '当前主机未正常同步，列表可能不是最新状态，请检查 Agent 地址和网络连通性。'
})

const statusTabs = computed(() => [
  { label: '全部', value: 'all', count: containers.value.length },
  { label: '运行中', value: 'running', count: containers.value.filter((item) => item.status === 'running').length },
  { label: '已停止', value: 'exited', count: containers.value.filter((item) => item.status === 'exited').length },
  { label: '异常', value: 'abnormal', count: containerSummary.value.abnormal },
])

const filteredContainers = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  let list = containers.value
  if (kw) {
    list = list.filter((item) => item.name.toLowerCase().includes(kw) || item.image.toLowerCase().includes(kw))
  }
  if (statusFilter.value === 'abnormal') {
    list = list.filter((item) => ['exited', 'dead', 'restarting', 'removing'].includes(item.status))
  } else if (statusFilter.value !== 'all') {
    list = list.filter((item) => item.status === statusFilter.value)
  }
  return sortContainersByRisk(list)
})

const pagedContainers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredContainers.value.slice(start, start + pageSize.value)
})

const overviewCards = computed(() => {
  const m = host.value.metrics || {}
  const diskPercent = m.disk_usage?.percent ?? null
  return [
    { label: 'CPU 使用率', value: m.cpu_percent != null ? m.cpu_percent.toFixed(1) + '%' : '-', percent: m.cpu_percent ?? null, valueClass: metricValueClass(m.cpu_percent), foot: `${m.cpu_count ?? '-'} 核` },
    { label: '内存使用率', value: m.memory_percent != null ? m.memory_percent.toFixed(1) + '%' : '-', percent: m.memory_percent ?? null, valueClass: metricValueClass(m.memory_percent), foot: m.memory_total ? formatBytes(m.memory_total) : '内存总量未知' },
    { label: '磁盘使用率', value: diskPercent != null ? diskPercent.toFixed(1) + '%' : '-', percent: diskPercent, valueClass: metricValueClass(diskPercent), foot: '主要数据分区' },
    { label: '容器总数', value: containerSummary.value.total, percent: null, valueClass: '', foot: `运行中 ${containerSummary.value.running}` },
    { label: '异常容器', value: containerSummary.value.abnormal, percent: null, valueClass: containerSummary.value.abnormal ? 'text-danger' : '', foot: `${containerSummary.value.exited} exited` },
    { label: '重启风险', value: containerSummary.value.restartRisk, percent: null, valueClass: containerSummary.value.restartRisk ? 'text-warning' : '', foot: '重启次数 > 3' },
  ]
})

const healthItems = computed(() => {
  const m = host.value.metrics || {}
  const diskPercent = m.disk_usage?.percent ?? 0
  return [
    { label: 'CPU', value: m.cpu_percent != null ? m.cpu_percent.toFixed(1) + '%' : '-', percent: Math.min(m.cpu_percent ?? 0, 100), barClass: healthBarClass(m.cpu_percent ?? 0) },
    { label: '内存', value: m.memory_percent != null ? m.memory_percent.toFixed(1) + '%' : '-', percent: Math.min(m.memory_percent ?? 0, 100), barClass: healthBarClass(m.memory_percent ?? 0) },
    { label: '磁盘', value: diskPercent ? diskPercent.toFixed(1) + '%' : '-', percent: Math.min(diskPercent, 100), barClass: healthBarClass(diskPercent) },
  ]
})

const healthTagType = computed(() => containerSummary.value.abnormal > 0 || healthItems.value.some((item) => item.percent > THRESHOLD_WARN) ? 'warning' : 'success')
const healthLabel = computed(() => healthTagType.value === 'warning' ? '关注' : '正常')
const actionSuggestion = computed(() => {
  if (containerSummary.value.abnormal > 0) return '优先查看异常容器日志，再执行重启或停止。'
  if (syncState.value !== 'fresh') return '先立即刷新，确认数据新鲜度。'
  return '主机状态平稳，保持自动同步即可。'
})

watch(keyword, () => { page.value = 1 })
watch(statusFilter, () => { page.value = 1 })

function progressColor(percent: number): string {
  if (percent > THRESHOLD_DANGER) return 'var(--danger-color)'
  if (percent > THRESHOLD_WARN) return 'var(--warning-color)'
  return 'var(--primary-color)'
}

function metricValueClass(percent?: number | null) {
  if (percent == null) return ''
  if (percent > THRESHOLD_DANGER) return 'text-danger'
  if (percent > THRESHOLD_WARN) return 'text-warning'
  return ''
}

function healthBarClass(percent: number) {
  if (percent > THRESHOLD_DANGER) return 'danger'
  if (percent > THRESHOLD_WARN) return 'warning'
  return ''
}

function endpointHost(endpoint = '') {
  const value = endpoint.replace(/^https?:\/\//, '')
  return value.split(':')[0]
}

function formatRelativeTime(ts?: string | null) {
  const seconds = secondsSince(ts)
  if (seconds == null) return '从未同步'
  if (seconds < 60) return `${seconds} 秒前`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.floor(hours / 24)} 天前`
}

function formatTime(ts: string) {
  if (!ts) return '-'
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function formatPorts(portsJson: string): string {
  if (!portsJson || portsJson === '{}') return '-'
  try {
    const ports = JSON.parse(portsJson)
    const mappings: string[] = []
    for (const [containerPort, bindings] of Object.entries(ports)) {
      if (Array.isArray(bindings) && bindings.length > 0) {
        for (const b of bindings) {
          mappings.push(`${b.HostIp || '0.0.0.0'}:${b.HostPort}->${containerPort}`)
        }
      } else {
        mappings.push(containerPort)
      }
    }
    return mappings.join(', ') || '-'
  } catch {
    return portsJson
  }
}

function containerStatusType(s: string) {
  if (s === 'running') return 'success'
  if (s === 'exited' || s === 'dead') return 'danger'
  if (s === 'paused' || s === 'restarting') return 'warning'
  return 'info'
}

function containerDotClass(s: string) {
  if (s === 'running') return 'dot-success'
  if (s === 'exited' || s === 'dead') return 'dot-danger'
  if (s === 'paused' || s === 'restarting') return 'dot-warning'
  return 'dot-info'
}

function containerStatusLabel(s: string) {
  if (s === 'running') return '运行中'
  if (s === 'exited') return '已停止'
  if (s === 'paused') return '暂停'
  if (s === 'restarting') return '重启中'
  return s
}

async function openContainerLogs(row: any) {
  // 切容器必须先关闭旧连接
  stopLiveFollow()
  inspectDrawerVisible.value = false
  selectedContainer.value = row
  containerLogs.value = ''
  logKeyword.value = ''
  logsDrawerVisible.value = true
  await fetchSelectedContainerLogs()
}

async function fetchSelectedContainerLogs() {
  if (!selectedContainer.value) return
  // 重新加载快照前停掉旧的实时连接（随后会重新开启）
  stopLiveFollow()
  logsLoading.value = true
  try {
    let res: any
    if (logMode.value === 'time') {
      const since = logTimeWindow.value === 0 ? 0 : Math.floor(Date.now() / 1000) - logTimeWindow.value
      res = await getDockerContainerLogs(hostName.value, selectedContainer.value.container_id, { since })
    } else {
      res = await getDockerContainerLogs(hostName.value, selectedContainer.value.container_id, { tail_lines: logTailLines.value })
    }
    containerLogs.value = res.data?.logs || ''
    await nextTick(() => scrollLogToBottom(true))
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载日志失败')
  } finally {
    logsLoading.value = false
  }
  // 以快照为起点开启近实时跟随（追加新行，不清空已有内容）
  if (logsDrawerVisible.value) startLiveFollow()
}

// ─── 实时跟随（SSE） ───────────────────────────────────────
function startLiveFollow() {
  if (!selectedContainer.value) return
  stopLiveFollow()
  // 以「现在」为游标；快照内容保留在前，新行追加其后
  liveSince = Math.floor(Date.now() / 1000)
  const url = buildDockerLogStreamUrl(hostName.value, selectedContainer.value.container_id, liveSince)
  logEs = new EventSource(url)
  liveActive.value = true
  logEs.onmessage = (ev) => {
    let data: any
    try {
      data = JSON.parse(ev.data)
    } catch {
      return
    }
    if (data.type === 'append') {
      const add = data.lines || ''
      if (!add) return
      containerLogs.value = containerLogs.value ? `${containerLogs.value}\n${add}` : add
      trimLogsTail()
      nextTick(() => scrollLogToBottom(false))
    } else if (data.type === 'error') {
      ElMessage.warning(data.message || '实时拉取出错')
    }
    // ready / heartbeat / done 不需要前端处理
  }
  logEs.onerror = () => {
    // 401（未登录/无权限）→ readyState=CLOSED 且不自动重连；暂态网络错误由浏览器自动重连
    if (logEs && logEs.readyState === EventSource.CLOSED) {
      liveActive.value = false
      ElMessage.error('实时连接已断开，请检查登录状态或权限')
      stopLiveFollow()
    }
  }
}

function stopLiveFollow() {
  liveActive.value = false
  if (logEs) {
    logEs.close()
    logEs = null
  }
}

function scrollLogToBottom(force = false) {
  const el = logScrollRef.value
  if (!el) return
  const nearBottom = force || el.scrollHeight - el.scrollTop - el.clientHeight < 60
  if (nearBottom) el.scrollTop = el.scrollHeight
}

function scrollLogToTop() {
  const el = logScrollRef.value
  if (el) el.scrollTop = 0
}

function trimLogsTail() {
  const lines = containerLogs.value.split('\n')
  if (lines.length > LIVE_LOG_MAX_LINES) {
    containerLogs.value = lines.slice(lines.length - LIVE_LOG_MAX_LINES).join('\n')
  }
}

function copyLogs() {
  if (!displayedContainerLogs.value) return
  navigator.clipboard.writeText(displayedContainerLogs.value).then(
    () => ElMessage.success('已复制到剪贴板'),
    () => ElMessage.error('复制失败'),
  )
}

function downloadLogs() {
  if (!displayedContainerLogs.value || !selectedContainer.value) return
  const blob = new Blob([displayedContainerLogs.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${selectedContainer.value.name || selectedContainer.value.container_id}.log`
  anchor.click()
  URL.revokeObjectURL(url)
}

// ─── 容器 inspect 详情 ────────────────────────────────────
const inspectDrawerVisible = ref(false)
const inspectLoading = ref(false)
const inspectData = ref<any>(null)
const inspectContainer = ref<any | null>(null)
const revealedEnvKeys = ref<Set<string>>(new Set())
const sectionCollapse = reactive({
  env: false,
  network: false,
  mounts: true,
  health: true,
  resources: true,
  labels: true,
})

// 含这些关键词的环境变量视为敏感，默认掩码，点击「显示」后明文
const SENSITIVE_ENV_RE = /(pass(word|wd)?|secret|token|api[-_]?key|credential|private[-_]?key|access[-_]?key|auth)/i

const inspectConfig = computed(() => inspectData.value?.Config || {})
const inspectState = computed(() => inspectData.value?.State || {})
const inspectHostConfig = computed(() => inspectData.value?.HostConfig || {})
const inspectNetwork = computed(() => inspectData.value?.NetworkSettings || {})
const inspectMounts = computed(() => inspectData.value?.Mounts || [])

const restartPolicyText = computed(() => {
  const rp = inspectHostConfig.value.RestartPolicy
  if (!rp || !rp.Name || rp.Name === 'no') return '不自动重启'
  if (rp.Name === 'on-failure') return `失败时重启${rp.MaximumRetryCount ? `（最多 ${rp.MaximumRetryCount} 次）` : ''}`
  if (rp.Name === 'always') return '始终重启'
  if (rp.Name === 'unless-stopped') return '除非手动停止否则重启'
  return rp.Name
})

function joinCmd(list?: string[] | null): string {
  return Array.isArray(list) && list.length ? list.join(' ') : '-'
}
const cmdText = computed(() => joinCmd(inspectConfig.value.Cmd))
const entrypointText = computed(() => joinCmd(inspectConfig.value.Entrypoint))

const envItems = computed(() => {
  const env: string[] = inspectConfig.value.Env || []
  return env.map((item) => {
    const idx = item.indexOf('=')
    const key = idx >= 0 ? item.slice(0, idx) : item
    const value = idx >= 0 ? item.slice(idx + 1) : ''
    return { key, value, sensitive: SENSITIVE_ENV_RE.test(key) }
  })
})

function envDisplayValue(item: { key: string; value: string; sensitive: boolean }) {
  if (item.sensitive && !revealedEnvKeys.value.has(item.key)) return '••••••••'
  return item.value || '(空)'
}

function toggleEnvReveal(key: string) {
  const next = new Set(revealedEnvKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  revealedEnvKeys.value = next
}

const portBindingsText = computed(() => formatPorts(JSON.stringify(inspectHostConfig.value.PortBindings || {})))
const linkedNetworks = computed(() => {
  const nets = inspectNetwork.value.Networks || {}
  return Object.entries(nets).map(([name, info]: [string, any]) => ({ name, ip: info?.IPAddress || '' }))
})
const networkSummary = computed(() => {
  const ip = inspectNetwork.value.IPAddress
  const portCount = Object.keys(inspectHostConfig.value.PortBindings || {}).length
  const parts: string[] = []
  if (ip) parts.push(`IP ${ip}`)
  if (portCount) parts.push(`${portCount} 个端口映射`)
  return parts.length ? parts.join(' · ') : (inspectHostConfig.value.NetworkMode || '默认网络')
})

const healthStatusLabel = computed(() => {
  const status = inspectState.value.Health?.Status
  if (!status) return '未配置'
  const map: Record<string, string> = { healthy: '健康', unhealthy: '异常', starting: '启动中', none: '无' }
  return map[status] || status
})
const inspectHealthTagType = computed(() => {
  const status = inspectState.value.Health?.Status
  if (status === 'healthy') return 'success'
  if (status === 'unhealthy') return 'danger'
  if (status === 'starting') return 'warning'
  return 'info'
})
const healthSummary = computed(() => {
  if (!inspectConfig.value.Healthcheck && !inspectState.value.Health) return '未配置'
  return healthStatusLabel.value
})
const healthcheckTestText = computed(() => joinCmd(inspectConfig.value.Healthcheck?.Test))
function nanoToSeconds(ns?: number): string {
  if (!ns || ns <= 0) return '-'
  return `${Math.round(ns / 1e9)}s`
}
const healthcheckIntervalText = computed(() => nanoToSeconds(inspectConfig.value.Healthcheck?.Interval))
const healthcheckTimeoutText = computed(() => nanoToSeconds(inspectConfig.value.Healthcheck?.Timeout))

const cpuLimitText = computed(() => {
  const nano = inspectHostConfig.value.NanoCpus
  return nano ? `${(nano / 1e9).toFixed(2)} 核` : '未限制'
})
const resourcesSummary = computed(() => {
  const mem = inspectHostConfig.value.Memory
  const nano = inspectHostConfig.value.NanoCpus
  return [
    mem ? `内存 ${formatBytes(mem)}` : '内存未限',
    nano ? `CPU ${(nano / 1e9).toFixed(2)} 核` : 'CPU 未限',
  ].join(' · ')
})
const labelEntries = computed(() => {
  const labels = inspectConfig.value.Labels || {}
  return Object.entries(labels).map(([key, value]: [string, any]) => ({ key, value: String(value ?? '') }))
})

function toggleSection(key: keyof typeof sectionCollapse) {
  sectionCollapse[key] = !sectionCollapse[key]
}

// Docker 时间可能带纳秒（>3 位小数），截断到毫秒避免 new Date 得到 Invalid Date
function formatInspectTime(ts?: string): string {
  if (!ts) return '-'
  const normalized = ts.replace(/(\.\d{3})\d+/, '$1')
  const d = new Date(normalized)
  return isNaN(d.getTime()) ? ts : d.toLocaleString('zh-CN')
}

async function openContainerInspect(row: any) {
  stopLiveFollow()
  logsDrawerVisible.value = false
  inspectContainer.value = row
  inspectData.value = null
  revealedEnvKeys.value = new Set()
  Object.assign(sectionCollapse, { env: false, network: false, mounts: true, health: true, resources: true, labels: true })
  inspectDrawerVisible.value = true
  await fetchContainerInspect()
}

async function fetchContainerInspect() {
  if (!inspectContainer.value) return
  inspectLoading.value = true
  try {
    const res: any = await getDockerContainerInspect(hostName.value, inspectContainer.value.container_id)
    inspectData.value = res.data?.inspect || null
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载容器详情失败')
    inspectData.value = null
  } finally {
    inspectLoading.value = false
  }
}

async function handleContainerAction(row: any, action: 'start' | 'stop' | 'restart' | 'delete') {
  const labels = { start: '启动', stop: '停止', restart: '重启', delete: '删除' }

  if (action === 'delete') {
    try {
      await ElMessageBox.confirm(`确定删除容器「${row.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
    } catch { return }
  }

  try {
    const apiMap = { start: startDockerContainer, stop: stopDockerContainer, restart: restartDockerContainer, delete: deleteDockerContainer }
    await apiMap[action](hostName.value, row.container_id)
    ElMessage.success(`${labels[action]}成功`)
    fetchContainers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || `${labels[action]}失败`)
  }
}

async function fetchHost() {
  if (!hostName.value) return false
  try {
    const res: any = await getDockerHost(hostName.value)
    host.value = res.data
    return true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '主机不存在')
    return false
  }
}

async function fetchContainers() {
  if (!hostName.value) return
  loading.value = true
  try {
    const res: any = await getHostContainers(hostName.value)
    containers.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadHostDetail() {
  const routeRef = hostName.value
  if (!routeRef || activeLoadRef === routeRef) return
  activeLoadRef = routeRef
  if (host.value.name && host.value.name !== routeRef) {
    host.value = {}
    containers.value = []
  }
  try {
    if (await fetchHost()) await fetchContainers()
  } finally {
    if (activeLoadRef === routeRef) activeLoadRef = ''
  }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await refreshDockerHost(hostName.value)
    await fetchHost()
    await fetchContainers()
    ElMessage.success('刷新成功')
  } catch {
    ElMessage.error('Agent 连接失败')
  } finally {
    refreshing.value = false
  }
}

async function handleDelete() {
  await ElMessageBox.confirm(`确定删除主机「${host.value.name}」？所有容器数据将被清除。`, '删除确认', { type: 'warning' })
  await deleteDockerHost(hostName.value)
  ElMessage.success('删除成功')
  router.push('/assets/docker')
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = setInterval(() => {
      fetchHost()
      fetchContainers()
    }, 15000)
  } else {
    stopAutoRefresh()
  }
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

let activeLoadRef = ''
watch(hostName, loadHostDetail)
// 抽屉关闭必须关闭 EventSource（destroy-on-close 只销毁 DOM，不关连接）
watch(logsDrawerVisible, (v) => {
  if (!v) stopLiveFollow()
})
watch(logKeyword, () => {
  nextTick(scrollLogToTop)
})

onActivated(loadHostDetail)

onDeactivated(() => {
  stopAutoRefresh()
  stopLiveFollow()
})

onUnmounted(() => {
  stopAutoRefresh()
  stopLiveFollow()
})
</script>

<style scoped>
.detail-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--surface-color);
  margin-bottom: 12px;
}
.detail-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}
.detail-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.field-label {
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 2px;
}
.field-value {
  color: var(--text-primary);
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.sync-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
  font-size: 13px;
}
.notice-info {
  background: var(--primary-bg);
  border-color: color-mix(in srgb, var(--primary-color), white 72%);
  color: var(--primary-color);
}
.notice-warning {
  background: color-mix(in srgb, var(--warning-color), white 91%);
  border-color: color-mix(in srgb, var(--warning-color), white 65%);
  color: #7a5100;
}
.notice-danger {
  background: color-mix(in srgb, var(--danger-color), white 93%);
  border-color: color-mix(in srgb, var(--danger-color), white 68%);
  color: #9f2227;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.metric-card {
  min-width: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
  overflow: hidden;
}
.metric-label {
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metric-value {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 750;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metric-foot {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stat-progress {
  margin-top: 6px;
}
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 12px;
}
.panel {
  min-width: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}
.panel-head.compact {
  align-items: center;
}
.panel-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}
.panel-subtitle {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}
.container-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.search-input {
  width: 240px;
}
.status-tabs {
  display: flex;
  gap: 4px;
  padding: 10px 12px 0;
}
.status-tab {
  height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}
.status-tab.active {
  background: var(--primary-bg);
  color: var(--primary-color);
  font-weight: 650;
}
.container-name {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.container-name strong,
.container-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.container-name span {
  color: var(--text-muted);
}
.memory-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.memory-progress {
  flex: 1;
}
.memory-text {
  font-size: 12px;
  white-space: nowrap;
}
.action-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 11px 12px;
  border-top: 1px solid var(--border-color);
}
.health-list {
  display: grid;
  gap: 10px;
  padding: 12px;
}
.health-item {
  display: grid;
  gap: 6px;
}
.health-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
}
.health-row strong {
  color: var(--text-primary);
}
.health-bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #eef0f4;
}
.health-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--primary-color);
}
.health-bar span.warning {
  background: var(--warning-color);
}
.health-bar span.danger {
  background: var(--danger-color);
}
.event-list {
  padding: 0 12px 12px;
}
.event-item {
  display: grid;
  gap: 3px;
  padding: 10px 0;
  border-top: 1px solid var(--border-color);
}
.event-item strong {
  font-size: 13px;
}
.event-item span {
  color: var(--text-muted);
  font-size: 12px;
}
.status-dot,
.tag-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  flex: none;
}
.tag-dot {
  display: inline-block;
  margin-right: 5px;
}
.dot-success { background: var(--success-color); }
.dot-warning { background: var(--warning-color); }
.dot-danger { background: var(--danger-color); }
.dot-info { background: var(--primary-color); }
.text-warning { color: var(--warning-color); }
.text-danger { color: var(--danger-color); }
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--border-color);
}
.drawer-head-copy {
  min-width: 0;
}
.drawer-head-copy h3 {
  margin: 0;
  font-size: 15px;
  word-break: break-all;
}
.drawer-sub {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.drawer-actions {
  display: flex;
  gap: 6px;
  flex: none;
}
:deep(.el-drawer__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
  overflow: hidden;
}
.drawer-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 18px;
}
.log-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  color: var(--text-secondary);
  font-size: 13px;
}
.log-tail-select {
  width: 120px;
}
.log-keyword-input {
  flex: 1 1 180px;
  max-width: 240px;
}
:deep(.log-keyword-match) {
  padding: 0 1px;
  color: var(--text-primary);
  background: color-mix(in srgb, var(--warning-color) 82%, var(--surface-color));
  border-radius: 2px;
}
.log-count {
  color: var(--text-muted);
  font-size: 12px;
}
.log-live {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: color-mix(in srgb, var(--border-color) 55%, transparent);
}
.log-live.is-live {
  color: color-mix(in srgb, var(--success-color) 65%, var(--text-primary));
  background: color-mix(in srgb, var(--success-color) 12%, transparent);
}
.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}
.log-live.is-live .live-dot {
  animation: live-pulse 1.6s ease-in-out infinite;
}
@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
.log-scroll {
  flex: 1;
  min-height: 0;
}
.log-box {
  height: 100%;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: #d1d5db;
  background: #111827;
  border-radius: var(--border-radius);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  outline: none;
}
.log-box:focus-visible {
  box-shadow: 0 0 0 2px var(--primary-color);
}
/* ─── 容器 inspect 详情 ─── */
.inspect-body {
  gap: 12px;
}
.inspect-section {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-color);
  overflow: hidden;
}
.inspect-section-title {
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
}
.inspect-section.collapsible .inspect-section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
}
.inspect-section.collapsible .inspect-section-head:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px var(--primary-color);
}
.inspect-section-head .inspect-section-title {
  flex: 1;
  padding: 0;
  border: 0;
  background: transparent;
}
.inspect-section-summary {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.inspect-caret {
  flex: none;
  color: var(--text-muted);
  transition: transform 0.2s ease-out;
}
.inspect-caret.open {
  transform: rotate(180deg);
}
.inspect-section-body {
  padding: 12px 14px;
}
.inspect-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
  margin: 0;
}
.inspect-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.inspect-field-wide {
  grid-column: 1 / -1;
}
.inspect-field dt {
  color: var(--text-muted);
  font-size: 12px;
}
.inspect-field dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 13px;
  word-break: break-word;
}
.kv-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.kv-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.kv-item-block {
  flex-wrap: wrap;
  justify-content: space-between;
}
.kv-key {
  color: var(--text-secondary);
  flex: none;
  max-width: 40%;
}
.kv-value {
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
}
.kv-value.masked {
  color: var(--text-muted);
  letter-spacing: 1px;
}
.kv-reveal {
  flex: none;
  padding: 0 4px;
  height: auto;
}
.kv-arrow {
  color: var(--text-muted);
  margin: 0 4px;
}
.kv-empty {
  color: var(--text-muted);
  font-size: 13px;
}
.inspect-sub {
  margin-top: 12px;
  display: grid;
  gap: 4px;
}
.inspect-sub-title {
  color: var(--text-muted);
  font-size: 12px;
}
.break-all {
  word-break: break-all;
}
@media (max-width: 768px) {
  .inspect-grid {
    grid-template-columns: 1fr;
  }
  .kv-key {
    max-width: 45%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .inspect-caret {
    transition: none;
  }
}
@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .detail-header,
  .panel-head {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .detail-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .header-actions,
  .container-tools,
  .search-input {
    width: 100%;
  }
  .header-actions,
  .container-tools {
    flex-wrap: wrap;
  }
  .log-keyword-input {
    max-width: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .log-live.is-live .live-dot {
    animation: none;
  }
}
</style>
