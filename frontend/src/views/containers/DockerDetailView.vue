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
            <el-table-column label="操作" width="340" fixed="right" align="right">
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
                    v-if="row.status === 'running'"
                    size="small"
                    type="primary"
                    link
                    :aria-label="`进入容器 ${row.name} 终端`"
                    @click.stop="openContainerExec(row)"
                  >终端</el-button>
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
          <el-tooltip content="在日志检索中查询该容器的历史日志（Elasticsearch）" placement="bottom">
            <el-button size="small" type="primary" plain @click="goDockerLogHistory(selectedContainer)">历史日志</el-button>
          </el-tooltip>
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
      <div class="di-head">
        <div class="di-head-copy">
          <div class="di-hero">
            <span class="di-phase" :class="containerStatusPhaseClass(inspectContainer?.status)">
              <span class="di-pdot" aria-hidden="true"></span>{{ inspectContainer ? containerStatusLabel(inspectContainer.status) : '-' }}
            </span>
            <span v-if="healthFlagText" class="di-flag" :class="healthFlagClass">{{ healthFlagText }}</span>
            <span v-if="(inspectState.RestartCount ?? 0) > 0" class="di-flag di-flag-warn">重启 {{ inspectState.RestartCount }} 次</span>
            <span v-if="inspectState.OOMKilled" class="di-flag di-flag-bad">曾 OOMKilled</span>
          </div>
          <h3 class="di-title">{{ inspectContainer?.name || '容器详情' }}</h3>
          <div class="di-chips">
            <span class="di-chip">
              <span class="di-ck">镜像</span><span class="mono">{{ inspectContainer?.image || '-' }}</span>
              <button v-if="inspectContainer?.image" type="button" class="di-chip-cp" :class="{ done: copiedKey === 'chip-image' }" :aria-label="copiedKey === 'chip-image' ? '已复制' : '复制镜像'" @click="copyText(inspectContainer.image, 'chip-image')">{{ copiedKey === 'chip-image' ? '✓' : '⧉' }}</button>
            </span>
            <span class="di-chip">
              <span class="di-ck">ID</span><span class="mono">{{ inspectShortId || '-' }}</span>
              <button v-if="inspectShortId" type="button" class="di-chip-cp" :class="{ done: copiedKey === 'chip-id' }" :aria-label="copiedKey === 'chip-id' ? '已复制' : '复制容器 ID'" @click="copyText(inspectShortId, 'chip-id')">{{ copiedKey === 'chip-id' ? '✓' : '⧉' }}</button>
            </span>
            <span class="di-chip"><span class="di-ck">启动</span>{{ inspectState.StartedAt ? formatRelativeTime(inspectState.StartedAt) : '-' }}</span>
            <span class="di-chip"><span class="di-ck">创建</span>{{ formatInspectTime(inspectData?.Created) }}</span>
          </div>
        </div>
        <div class="di-head-actions">
          <el-button size="small" type="primary" plain @click="openContainerLogs(inspectContainer)">日志</el-button>
          <el-tooltip content="在日志检索中查询该容器的历史日志（Elasticsearch）" placement="bottom">
            <el-button size="small" plain @click="goDockerLogHistory(inspectContainer)">历史日志</el-button>
          </el-tooltip>
          <el-button size="small" :disabled="inspectContainer?.status !== 'running'" @click="openContainerExec(inspectContainer)">终端</el-button>
          <el-button size="small" :loading="inspectLoading" @click="fetchContainerInspect">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
          <button type="button" class="di-close" aria-label="关闭" @click="inspectDrawerVisible = false">✕</button>
        </div>
      </div>

      <div class="di-stat-strip">
        <div class="di-stat">
          <div class="di-stat-k">运行时长</div>
          <div class="di-stat-v">{{ inspectUptimeText }}</div>
          <div class="di-stat-sub">PID {{ inspectState.Pid ?? '-' }} · 退出码 {{ inspectState.ExitCode ?? '-' }}</div>
        </div>
        <div class="di-stat">
          <div class="di-stat-k">重启次数</div>
          <div class="di-stat-v" :class="{ 'is-warn': (inspectState.RestartCount ?? 0) > 0 }">{{ inspectState.RestartCount ?? 0 }}</div>
          <div class="di-stat-sub">{{ restartPolicyText }}</div>
        </div>
        <div class="di-stat">
          <div class="di-stat-k">健康状态</div>
          <div class="di-stat-v sm" :class="healthValueClass">{{ healthStatusLabel }}</div>
          <div v-if="healthFailingStreak > 0" class="di-stat-sub">连续失败 {{ healthFailingStreak }} 次</div>
        </div>
        <div class="di-stat">
          <div class="di-stat-k">OOM</div>
          <div class="di-stat-v sm" :class="inspectState.OOMKilled ? 'is-bad' : 'is-ok'">{{ inspectState.OOMKilled ? '曾被终止' : '未触发' }}</div>
        </div>
      </div>

      <div class="di-anchors" role="navigation" aria-label="详情区块导航">
        <button type="button" class="di-anchor" @click="scrollDiSection('trend')">概览</button>
        <button type="button" class="di-anchor" @click="scrollDiSection('network')">网络</button>
        <button type="button" class="di-anchor" @click="scrollDiSection('resources')">资源</button>
        <button type="button" class="di-anchor" @click="scrollDiSection('health')">健康检查</button>
        <button type="button" class="di-anchor" @click="scrollDiSection('config')">配置</button>
      </div>

      <div class="di-body" v-loading="inspectLoading">
        <div class="di-scroll">
          <section class="di-section" id="di-sec-trend">
            <header class="di-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.trend" @click="toggleSection('trend')" @keyup.enter="toggleSection('trend')">
              <h4 class="di-section-title">指标趋势</h4>
              <span class="di-section-meta">{{ inspectTrendRangeText || '近 1 小时' }}</span>
              <el-icon class="di-caret" :class="{ open: !sectionCollapse.trend }" aria-hidden="true"><ArrowDown /></el-icon>
            </header>
            <div v-show="!sectionCollapse.trend" class="di-trend-body">
              <MetricTrendChart
                :series="inspectTrendData?.series || []"
                :loading="inspectTrendLoading"
                :range-minutes="inspectTrendData?.range_minutes || 60"
                :columns="2"
                empty-hint="暂无历史指标（后台每分钟采样，需运行一段时间）"
              />
            </div>
          </section>
          <template v-if="inspectData">
            <section class="di-section" id="di-sec-network">
              <header class="di-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.network" @click="toggleSection('network')" @keyup.enter="toggleSection('network')">
                <h4 class="di-section-title">网络</h4>
                <span class="di-section-meta">{{ networkSummary }}</span>
                <el-icon class="di-caret" :class="{ open: !sectionCollapse.network }" aria-hidden="true"><ArrowDown /></el-icon>
              </header>
              <div v-show="!sectionCollapse.network" class="di-card">
                <div class="di-net-grid">
                  <div class="di-net"><div class="di-net-k">IP 地址</div><div class="di-net-v mono">{{ inspectNetwork.IPAddress || '-' }}</div></div>
                  <div class="di-net"><div class="di-net-k">网络模式</div><div class="di-net-v mono">{{ inspectHostConfig.NetworkMode || '-' }}</div></div>
                  <div class="di-net"><div class="di-net-k">MAC 地址</div><div class="di-net-v mono">{{ inspectNetwork.MacAddress || '-' }}</div></div>
                  <div class="di-net"><div class="di-net-k">网关</div><div class="di-net-v mono">{{ inspectNetwork.Gateway || '-' }}</div></div>
                </div>
                <div v-if="portList.length" class="di-sub">
                  <div class="di-sub-k">端口映射</div>
                  <div class="di-ports">
                    <span v-for="(p, i) in portList" :key="i" class="di-port">
                      <span class="mono">{{ p.host }}</span><span class="di-port-arr">→</span><span class="mono di-port-ctr">{{ p.ctr }}</span><span class="di-port-proto">{{ p.proto }}</span>
                    </span>
                  </div>
                </div>
                <div v-if="linkedNetworks.length" class="di-sub">
                  <div class="di-sub-k">连接的网络</div>
                  <div v-for="n in linkedNetworks" :key="n.name" class="mono di-line">{{ n.name }}<template v-if="n.ip"> · {{ n.ip }}</template></div>
                </div>
              </div>
            </section>

            <section class="di-section" id="di-sec-resources">
              <header class="di-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.resources" @click="toggleSection('resources')" @keyup.enter="toggleSection('resources')">
                <h4 class="di-section-title">资源限制</h4>
                <span class="di-section-meta">{{ resourcesSummary }}</span>
                <el-icon class="di-caret" :class="{ open: !sectionCollapse.resources }" aria-hidden="true"><ArrowDown /></el-icon>
              </header>
              <div v-show="!sectionCollapse.resources" class="di-card">
                <div v-if="inspectResBars.mem.show || inspectResBars.cpu.show" class="di-res-bars">
                  <div v-if="inspectResBars.cpu.show" class="di-res-bar">
                    <div class="di-res-top"><span class="di-res-k">CPU 限额</span><span class="di-res-v mono">{{ cpuLimitText }} / {{ hostCpuCount }} 核</span></div>
                    <div class="di-res-track"><i :class="barLevel(inspectResBars.cpu.percent)" :style="{ width: inspectResBars.cpu.percent + '%' }"></i></div>
                  </div>
                  <div v-if="inspectResBars.mem.show" class="di-res-bar">
                    <div class="di-res-top"><span class="di-res-k">内存限额</span><span class="di-res-v mono">{{ inspectHostConfig.Memory ? formatBytes(inspectHostConfig.Memory) : '-' }} / {{ hostMemTotalText }}</span></div>
                    <div class="di-res-track"><i :class="barLevel(inspectResBars.mem.percent)" :style="{ width: inspectResBars.mem.percent + '%' }"></i></div>
                  </div>
                </div>
                <dl class="di-kv-grid">
                  <div class="di-kv"><dt>CPU 权重</dt><dd class="mono">{{ inspectHostConfig.CpuShares || '-' }}</dd></div>
                  <div class="di-kv"><dt>PID 限制</dt><dd class="mono">{{ (inspectHostConfig.PidsLimit ?? 0) > 0 ? inspectHostConfig.PidsLimit : '未限制' }}</dd></div>
                  <div class="di-kv"><dt>OOM 禁杀</dt><dd>{{ inspectHostConfig.OomKillDisable ? '是' : '否' }}</dd></div>
                  <div class="di-kv"><dt>内存预留</dt><dd class="mono">{{ inspectHostConfig.MemoryReservation ? formatBytes(inspectHostConfig.MemoryReservation) : '0 B' }}</dd></div>
                </dl>
              </div>
            </section>

            <section class="di-section" id="di-sec-health">
              <header class="di-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.health" @click="toggleSection('health')" @keyup.enter="toggleSection('health')">
                <h4 class="di-section-title">健康检查</h4>
                <span class="di-section-meta">{{ healthSummary }}</span>
                <el-icon class="di-caret" :class="{ open: !sectionCollapse.health }" aria-hidden="true"><ArrowDown /></el-icon>
              </header>
              <div v-show="!sectionCollapse.health" class="di-health-wrap">
                <div v-if="inspectConfig.Healthcheck || inspectState.Health" class="di-health-banner" :class="healthBannerClass">
                  <span>{{ healthBannerIcon }} {{ healthStatusLabel }}</span>
                  <span v-if="inspectState.Health?.FailingStreak != null" class="di-hb-streak">{{ inspectState.Health.FailingStreak > 0 ? `连续失败 ${inspectState.Health.FailingStreak}` : '连续成功' }}</span>
                </div>
                <div v-if="inspectConfig.Healthcheck || inspectState.Health" class="di-card">
                  <dl class="di-kv-grid">
                    <div class="di-kv wide">
                      <dt>探针命令</dt>
                      <dd>
                        <span class="di-copy">
                          <span class="mono">{{ healthcheckTestText }}</span>
                          <button type="button" class="di-copy-btn" :class="{ done: copiedKey === 'probe' }" :aria-label="copiedKey === 'probe' ? '已复制' : '复制探针命令'" @click="copyText(healthcheckTestText, 'probe')">{{ copiedKey === 'probe' ? '✓' : '⧉' }}</button>
                        </span>
                      </dd>
                    </div>
                    <div class="di-kv"><dt>检测间隔</dt><dd class="mono">{{ healthcheckIntervalText }}</dd></div>
                    <div class="di-kv"><dt>超时</dt><dd class="mono">{{ healthcheckTimeoutText }}</dd></div>
                    <div class="di-kv"><dt>重试次数</dt><dd class="mono">{{ inspectConfig.Healthcheck?.Retries ?? '-' }}</dd></div>
                  </dl>
                </div>
                <div v-else class="di-card"><div class="di-empty">未配置健康检查</div></div>
              </div>
            </section>

            <section class="di-section" id="di-sec-config">
              <header class="di-section-head" role="button" tabindex="0" :aria-expanded="!sectionCollapse.config" @click="toggleSection('config')" @keyup.enter="toggleSection('config')">
                <h4 class="di-section-title">运行配置</h4>
                <span class="di-section-meta">命令 · 挂载 {{ inspectMounts.length }} · 环境变量 {{ envItems.length }} · 标签 {{ labelEntries.length }}</span>
                <el-icon class="di-caret" :class="{ open: !sectionCollapse.config }" aria-hidden="true"><ArrowDown /></el-icon>
              </header>
              <div v-show="!sectionCollapse.config">
                <div class="di-codeblock"><span class="di-code-k">ENTRYPOINT</span><span class="mono">{{ entrypointText }}</span></div>
                <div class="di-codeblock"><span class="di-code-k">CMD</span><span class="mono">{{ cmdText }}</span></div>
                <div class="di-card">
                  <dl class="di-kv-grid">
                    <div class="di-kv"><dt>工作目录</dt><dd class="mono">{{ inspectConfig.WorkingDir || '/' }}</dd></div>
                    <div class="di-kv"><dt>运行用户</dt><dd class="mono">{{ inspectConfig.User || 'root' }}</dd></div>
                    <div class="di-kv"><dt>TTY</dt><dd>{{ inspectConfig.Tty ? '是' : '否' }}</dd></div>
                    <div class="di-kv"><dt>交互 STDIN</dt><dd>{{ inspectConfig.OpenStdin ? '是' : '否' }}</dd></div>
                  </dl>
                  <div class="di-sub">
                    <div class="di-sub-k">挂载（{{ inspectMounts.length }}）</div>
                    <div v-for="(m, i) in inspectMounts" :key="i" class="di-mount">
                      <span class="mono">{{ m.Source || m.Name }} <span class="di-arrow">→</span> {{ m.Destination }}</span>
                      <span class="di-mount-tag">{{ m.Type || 'bind' }}{{ m.RW === false ? ' · 只读' : '' }}</span>
                    </div>
                    <div v-if="!inspectMounts.length" class="di-empty">无挂载</div>
                  </div>
                  <div class="di-sub">
                    <div class="di-sub-k">环境变量（{{ envItems.length }}）</div>
                    <ul v-if="envItems.length" class="di-env-list">
                      <li v-for="item in envItems" :key="item.key" class="di-env-row">
                        <span class="di-env-key mono">{{ item.key }}</span>
                        <span class="di-env-val mono" :class="{ masked: item.sensitive && !revealedEnvKeys.has(item.key) }">{{ envDisplayValue(item) }}</span>
                        <el-button v-if="item.sensitive" link size="small" class="di-env-reveal" :aria-label="revealedEnvKeys.has(item.key) ? `隐藏 ${item.key}` : `显示 ${item.key}`" @click="toggleEnvReveal(item.key)">{{ revealedEnvKeys.has(item.key) ? '隐藏' : '显示' }}</el-button>
                      </li>
                    </ul>
                    <div v-else class="di-empty">无环境变量</div>
                  </div>
                  <div class="di-sub">
                    <div class="di-sub-k">标签（{{ labelEntries.length }}）</div>
                    <div class="di-label-cloud">
                      <span v-for="item in labelEntries" :key="item.key" class="di-label"><span class="di-lk mono">{{ item.key }}</span><span class="di-lv mono">{{ item.value || '(空)' }}</span></span>
                      <span v-if="!labelEntries.length" class="di-empty">无标签</span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </template>
          <el-empty v-else-if="!inspectLoading" description="暂无详情数据" />
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="execVisible" title="容器终端" width="780px" :close-on-click-modal="false" destroy-on-close>
      <ExecPane v-if="execVisible && execUrl" :ws-url="execUrl" :title="execTitle" />
      <div class="exec-tip">默认进入 <code>/bin/sh</code>，如需 bash 可在终端内执行 <code>bash</code>。</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onActivated, onDeactivated, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowDown, Refresh, Search } from '@element-plus/icons-vue'
import LogHighlightedText from '@/components/LogHighlightedText'
import MetricTrendChart from '@/components/MetricTrendChart.vue'
import ExecPane from '@/components/ExecPane.vue'
import {
  getDockerHost,
  deleteDockerHost,
  refreshDockerHost,
  getHostContainers,
  getDockerContainerLogs,
  getDockerContainerInspect,
  getDockerContainerTrends,
  buildDockerLogStreamUrl,
  buildDockerExecWsUrl,
  startDockerContainer,
  stopDockerContainer,
  restartDockerContainer,
  deleteDockerContainer,
} from '@/api/containers'
import type { HostTrendData } from '@/api/monitoring'
import { getHostSyncState, secondsSince, sortContainersByRisk, summarizeContainers } from '@/utils/dockerMonitor'
import { useLiveLogs } from '@/composables/useLiveLogs'

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
const {
  logs: containerLogs,
  loading: logsLoading,
  logKeyword,
  logMode,
  logTailLines,
  logTimeWindow,
  liveActive,
  logScrollRef,
  totalLineCount: logLineCount,
  normalizedKeyword: normalizedLogKeyword,
  displayedLogs: displayedContainerLogs,
  highlightedLines: highlightedContainerLogLines,
  displayedLineCount: displayedLogLineCount,
  displayText: logDisplayText,
  countLabel: logCountLabel,
  fetch: fetchSelectedContainerLogs,
  startLive: startLiveFollow,
  stopLive: stopLiveFollow,
  scrollToBottom: scrollLogToBottom,
  scrollToTop: scrollLogToTop,
  copy: copyLogs,
  download: downloadLogs,
} = useLiveLogs({
  fetchSnapshot: (params) => selectedContainer.value
    ? getDockerContainerLogs(hostName.value, selectedContainer.value.container_id, params)
    : Promise.resolve({ data: { logs: '' } }),
  buildStreamUrl: (sinceUnix) => selectedContainer.value
    ? buildDockerLogStreamUrl(hostName.value, selectedContainer.value.container_id, sinceUnix)
    : '',
  drawerVisibleRef: logsDrawerVisible,
  getDownloadName: () => selectedContainer.value?.name || selectedContainer.value?.container_id || 'container',
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

function goDockerLogHistory(container: any) {
  // 跳转到日志检索页（Elasticsearch 数据源）。
  // K8s 托管容器的 Docker 名格式为 k8s_<容器>_<Pod>_<命名空间>_<UID>_<序号>
  // （k8s 资源名不允许下划线，按 _ 切分无歧义），可反解出三维精确过滤；
  // 独立 Docker 容器按主机维度兜底。
  if (!container?.name) return
  const query: Record<string, string> = {}
  const parts = String(container.name).split('_')
  if (parts.length === 6 && parts[0] === 'k8s') {
    query.namespace = parts[3]
    query.pod = parts[2]
    query.container = parts[1]
  } else if (hostName.value) {
    query.host = hostName.value
  }
  router.push({ path: '/monitoring/logs', query })
}

// ─── 容器 inspect 详情 ────────────────────────────────────
const inspectDrawerVisible = ref(false)
const inspectLoading = ref(false)
const inspectData = ref<any>(null)
const inspectContainer = ref<any | null>(null)
const revealedEnvKeys = ref<Set<string>>(new Set())
const sectionCollapse = reactive({
  trend: true,
  network: false,
  health: false,
  resources: false,
  config: true,
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

// ── 抽屉头部摘要 / 资源条 / 端口 ──
const inspectShortId = computed(() => (inspectData.value?.Id || '').slice(0, 12))

function containerStatusPhaseClass(s?: string) {
  if (s === 'running') return 'di-ok'
  if (s === 'exited' || s === 'dead') return 'di-bad'
  if (s === 'paused' || s === 'restarting') return 'di-warn'
  return 'di-info'
}

const healthFlagText = computed(() => {
  const st = inspectState.value.Health?.Status
  if (!st || st === 'none') return ''
  if (st === 'healthy') return '健康'
  if (st === 'unhealthy') return '异常'
  if (st === 'starting') return '启动中'
  return ''
})
const healthFlagClass = computed(() => {
  const t = inspectHealthTagType.value
  if (t === 'success') return 'di-flag-ok'
  if (t === 'danger') return 'di-flag-bad'
  if (t === 'warning') return 'di-flag-warn'
  return 'di-flag-info'
})
const healthValueClass = computed(() => {
  const t = inspectHealthTagType.value
  if (t === 'success') return 'is-ok'
  if (t === 'danger') return 'is-bad'
  if (t === 'warning') return 'is-warn'
  return ''
})
const healthBannerClass = computed(() => {
  const t = inspectHealthTagType.value
  if (t === 'success') return 'ok'
  if (t === 'danger') return 'bad'
  if (t === 'warning') return 'warn'
  return 'none'
})
const healthBannerIcon = computed(() => {
  const t = inspectHealthTagType.value
  if (t === 'success') return '✓'
  if (t === 'danger') return '✕'
  if (t === 'warning') return '⋯'
  return '•'
})

const hostCpuCount = computed(() => host.value?.metrics?.cpu_count || 0)
const hostMemTotalText = computed(() => {
  const t = host.value?.metrics?.memory_total
  return t ? formatBytes(t) : '未知'
})
const inspectResBars = computed(() => {
  const m = host.value?.metrics || {}
  const memLim = Number(inspectHostConfig.value.Memory) || 0
  const cpuCores = inspectHostConfig.value.NanoCpus ? inspectHostConfig.value.NanoCpus / 1e9 : 0
  const memTotal = Number(m.memory_total) || 0
  const cpuCount = Number(m.cpu_count) || 0
  const mem = (memLim && memTotal) ? { show: true, percent: Math.max(2, Math.min(100, Math.round(memLim / memTotal * 100))) } : { show: false, percent: 0 }
  const cpu = (cpuCores && cpuCount) ? { show: true, percent: Math.max(2, Math.min(100, Math.round(cpuCores / cpuCount * 100))) } : { show: false, percent: 0 }
  return { mem, cpu }
})
function barLevel(p: number) {
  if (p >= 90) return 'hot'
  if (p >= 70) return 'warn'
  return 'ok'
}

const portList = computed(() => {
  const pb = inspectHostConfig.value.PortBindings || {}
  const out: { host: string; ctr: string; proto: string }[] = []
  for (const [ctr, bindings] of Object.entries(pb)) {
    const arr = bindings as any[]
    if (Array.isArray(arr) && arr.length) {
      for (const b of arr) {
        out.push({ host: `${b.HostIp || '0.0.0.0'}:${b.HostPort}`, ctr, proto: b.Protocol || 'tcp' })
      }
    } else {
      out.push({ host: '-', ctr, proto: 'tcp' })
    }
  }
  return out
})

const copiedKey = ref('')
function copyText(text: string, key: string) {
  if (!text) return
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(
      () => { copiedKey.value = key; setTimeout(() => { if (copiedKey.value === key) copiedKey.value = '' }, 1100) },
      () => ElMessage.error('复制失败'),
    )
  } else {
    ElMessage.warning('当前环境不支持复制')
  }
}

function toggleSection(key: keyof typeof sectionCollapse) {
  sectionCollapse[key] = !sectionCollapse[key]
}

function scrollDiSection(key: string) {
  // 折叠的区块先展开再滚动定位
  if (key in sectionCollapse && sectionCollapse[key as keyof typeof sectionCollapse]) {
    sectionCollapse[key as keyof typeof sectionCollapse] = false
  }
  nextTick(() => {
    document.getElementById(`di-sec-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

const healthFailingStreak = computed(() => Number(inspectState.value.Health?.FailingStreak) || 0)

// 运行时长（基于 StartedAt，Docker 时间可能带纳秒需截断）
const inspectUptimeText = computed(() => {
  const t = inspectState.value.StartedAt
  if (!t || !inspectState.value.Running) return '-'
  const d = new Date(t.replace(/(\.\d{3})\d+/, '$1'))
  const ms = Date.now() - d.getTime()
  if (isNaN(ms) || ms < 0) return '-'
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h${m % 60 ? ` ${m % 60}m` : ''}`
  return `${Math.floor(h / 24)}d ${h % 24}h`
})

// Docker 时间可能带纳秒（>3 位小数），截断到毫秒避免 new Date 得到 Invalid Date
function formatInspectTime(ts?: string): string {
  if (!ts) return '-'
  const normalized = ts.replace(/(\.\d{3})\d+/, '$1')
  const d = new Date(normalized)
  return isNaN(d.getTime()) ? ts : d.toLocaleString('zh-CN')
}

const inspectTrendData = ref<HostTrendData | null>(null)
const inspectTrendLoading = ref(false)
const inspectTrendRangeText = computed(() => {
  const m = inspectTrendData.value?.range_minutes
  if (!m) return ''
  return m >= 60 ? `近 ${Math.max(1, Math.round(m / 60))} 小时` : `近 ${m} 分钟`
})
async function loadInspectTrends() {
  if (!inspectContainer.value) return
  inspectTrendLoading.value = true
  try {
    const res: any = await getDockerContainerTrends(hostName.value, inspectContainer.value.container_id, { minutes: 60 })
    inspectTrendData.value = res.data || null
  } catch {
    inspectTrendData.value = null
  } finally {
    inspectTrendLoading.value = false
  }
}

const execVisible = ref(false)
const execUrl = ref('')
const execTitle = ref('')
function openContainerExec(row: any) {
  if (row.status !== 'running') {
    ElMessage.warning('仅运行中的容器可进入终端')
    return
  }
  execTitle.value = `${row.name || row.container_id} · ${host.value?.name || ''}`
  execUrl.value = buildDockerExecWsUrl(hostName.value, row.container_id, '/bin/sh')
  execVisible.value = true
}

async function openContainerInspect(row: any) {
  stopLiveFollow()
  logsDrawerVisible.value = false
  inspectContainer.value = row
  inspectData.value = null
  inspectTrendData.value = null
  revealedEnvKeys.value = new Set()
  Object.assign(sectionCollapse, { env: true, network: false, mounts: true, health: false, resources: false, labels: true, runconfig: true })
  inspectDrawerVisible.value = true
  await fetchContainerInspect()
  loadInspectTrends()
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
/* ─── 容器 inspect 详情（v2：样式与 mockups/detail-drawer-v2.html 对齐） ─── */
.di-head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  padding: 16px 20px 14px;
  background: linear-gradient(180deg, #fbfbfc 0%, var(--surface-color) 100%);
  border-bottom: 1px solid var(--border-color);
}
.di-head-copy { min-width: 0; flex: 1; }
.di-hero { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.di-phase {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11.5px; font-weight: 600; padding: 2px 10px; border-radius: 999px;
}
.di-phase .di-pdot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.di-phase.di-ok { color: #16a34a; background: rgba(34, 197, 94, 0.11); }
.di-phase.di-bad { color: #dc2626; background: rgba(239, 68, 68, 0.09); }
.di-phase.di-warn { color: #d97706; background: rgba(245, 158, 11, 0.13); }
.di-phase.di-info { color: var(--text-secondary); background: color-mix(in srgb, var(--text-muted) 12%, white); }
.di-flag { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }
.di-flag-ok { color: #16a34a; background: rgba(34, 197, 94, 0.11); }
.di-flag-bad { color: #dc2626; background: rgba(239, 68, 68, 0.09); }
.di-flag-warn { color: #d97706; background: rgba(245, 158, 11, 0.13); }
.di-flag-info { color: var(--text-secondary); background: color-mix(in srgb, var(--text-muted) 12%, white); }
.di-title { margin: 0; font-size: 16px; font-weight: 700; letter-spacing: -0.01em; word-break: break-all; line-height: 1.3; }
.di-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.di-chip {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--bg-color); border: 1px solid var(--border-color);
  border-radius: 6px; padding: 2px 8px; font-size: 11.5px; color: var(--text-secondary);
}
.di-chip .di-ck { color: var(--text-muted); }
.di-chip-cp {
  border: 0; background: transparent; cursor: pointer; color: var(--text-muted); flex: none;
  width: 18px; height: 18px; border-radius: 4px; display: grid; place-items: center;
  font-size: 10px; line-height: 1; opacity: 0; transition: all 0.15s;
}
.di-chip:hover .di-chip-cp { opacity: 1; }
.di-chip-cp:hover { background: var(--primary-bg); color: var(--primary-color); }
.di-chip-cp.done { opacity: 1; color: var(--success-color); }
.di-head-actions { display: flex; gap: 6px; align-items: center; flex: none; }
.di-close {
  border: 0; cursor: pointer; width: 28px; height: 28px; border-radius: 7px;
  background: var(--bg-color); color: var(--text-secondary); font-size: 14px; line-height: 1;
  display: grid; place-items: center; transition: all 0.15s ease-out;
}
.di-close:hover { background: rgba(239, 68, 68, 0.09); color: #dc2626; }

/* KPI 条 */
.di-stat-strip {
  display: grid; grid-template-columns: repeat(4, 1fr);
  margin: 14px 20px 0;
  border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden;
  background: var(--surface-color);
}
.di-stat { padding: 10px 14px; border-right: 1px solid var(--border-color); }
.di-stat:last-child { border-right: none; }
.di-stat-k { font-size: 11px; color: var(--text-muted); margin-bottom: 2px; }
.di-stat-v { font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--text-primary); }
.di-stat-v.sm { font-size: 15px; }
.di-stat-v.is-ok { color: #16a34a; }
.di-stat-v.is-bad { color: #dc2626; }
.di-stat-v.is-warn { color: #d97706; }
.di-stat-sub { font-size: 11px; color: var(--text-muted); margin-top: 1px; }
.is-danger { color: var(--danger-color) !important; }

/* 锚点导航 */
.di-anchors {
  display: flex; align-items: center; gap: 4px;
  margin-top: 14px; padding: 8px 20px;
  background: var(--surface-color); border-bottom: 1px solid var(--border-color);
}
.di-anchor {
  border: 0; background: transparent; cursor: pointer;
  font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 4px 12px; border-radius: 6px; transition: all 0.12s;
}
.di-anchor:hover { color: var(--primary-color); background: var(--primary-bg); }

.di-body { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.di-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 20px 24px; background: var(--surface-color); }
.di-scroll::-webkit-scrollbar { width: 10px; }
.di-scroll::-webkit-scrollbar-thumb { background: #d4d4d8; border-radius: 6px; border: 3px solid var(--surface-color); }

.di-section { margin-top: 14px; }
.di-section-head {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; margin: 0 -10px 8px; border-radius: 8px;
  cursor: pointer; user-select: none;
}
.di-section-head:hover { background: var(--bg-color); }
.di-section-title { margin: 0; font-size: 13px; font-weight: 700; color: var(--text-primary); }
.di-section-meta { font-size: 11.5px; color: var(--text-muted); font-weight: 500; }
.di-caret { margin-left: auto; color: var(--text-muted); transition: transform 0.15s ease-out; font-size: 11px; flex: none; }
.di-caret.open { transform: rotate(180deg); }

.di-card { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 14px; }

/* 键值网格 */
.di-kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; margin: 0; }
.di-kv { display: flex; align-items: baseline; gap: 10px; font-size: 12.5px; min-width: 0; }
.di-kv.wide { grid-column: 1 / -1; }
.di-kv dt { flex: none; width: 76px; color: var(--text-muted); font-size: 12.5px; }
.di-kv dd { margin: 0; flex: 1; min-width: 0; color: var(--text-primary); font-size: 12.5px; word-break: break-all; }
.di-copy { display: inline-flex; align-items: center; gap: 5px; min-width: 0; max-width: 100%; }
.di-copy .mono { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.di-copy-btn {
  border: 0; background: transparent; cursor: pointer; color: var(--text-muted); flex: none;
  width: 22px; height: 22px; border-radius: 6px; display: grid; place-items: center;
  font-size: 11px; transition: all 0.15s;
}
.di-copy-btn:hover { background: var(--primary-bg); color: var(--primary-color); }
.di-copy-btn.done { color: var(--success-color); }

.di-sub { margin-top: 12px; display: block; }
.di-sub-k { font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.4px; margin-bottom: 6px; }
.di-line { color: var(--text-secondary); font-size: 12px; padding: 3px 0; }

/* 网络单元（扁平 kv 风） */
.di-net-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
.di-net { display: flex; align-items: baseline; gap: 10px; font-size: 12.5px; min-width: 0; }
.di-net-k { flex: none; width: 76px; color: var(--text-muted); font-size: 12.5px; }
.di-net-v { min-width: 0; color: var(--text-primary); font-size: 12.5px; word-break: break-all; }

/* 端口胶囊 */
.di-ports { display: flex; flex-wrap: wrap; gap: 6px; }
.di-port {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: 7px; padding: 3px 9px; font-size: 11.5px;
}
.di-port-arr { color: var(--primary-color); font-weight: 700; }
.di-port-ctr { color: var(--text-secondary); }
.di-port-proto { font-size: 10px; color: var(--text-muted); background: var(--bg-color); border-radius: 3px; padding: 0 4px; }

/* 资源条 */
.di-res-bars { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
.di-res-bar { min-width: 0; }
.di-res-top { display: flex; justify-content: space-between; align-items: baseline; font-size: 11.5px; margin-bottom: 4px; }
.di-res-k { color: var(--text-muted); }
.di-res-v { color: var(--text-secondary); }
.di-res-track { height: 5px; border-radius: 3px; background: #ececf2; overflow: hidden; }
.di-res-track i { display: block; height: 100%; border-radius: 3px; background: var(--primary-color); }
.di-res-track i.ok { background: var(--primary-color); }
.di-res-track i.warn { background: #d97706; }
.di-res-track i.hot { background: #dc2626; }

/* 健康条幅 */
.di-health-wrap { display: grid; gap: 10px; }
.di-health-banner {
  display: flex; align-items: center; gap: 10px; padding: 9px 13px; border-radius: 8px;
  font-size: 12.5px; font-weight: 600;
}
.di-health-banner.ok { background: rgba(34, 197, 94, 0.11); color: #16a34a; }
.di-health-banner.bad { background: rgba(239, 68, 68, 0.09); color: #dc2626; }
.di-health-banner.warn { background: rgba(245, 158, 11, 0.13); color: #d97706; }
.di-health-banner.none { background: color-mix(in srgb, var(--text-muted) 10%, white); color: var(--text-secondary); }
.di-hb-streak { margin-left: auto; font-size: 11.5px; opacity: 0.85; }

/* 代码块 */
.di-codeblock {
  display: flex; align-items: baseline; gap: 10px;
  background: #1c1c22; color: #d5d5de; padding: 8px 12px; border-radius: 8px;
  font-size: 11.5px; line-height: 1.6; word-break: break-word;
  margin-bottom: 8px;
}
.di-codeblock:last-child { margin-bottom: 0; }
.di-codeblock .mono { color: inherit; }
.di-code-k { color: #7d7d92; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; flex: none; }

/* 挂载（扁平虚线行） */
.di-mount {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-size: 12px; padding: 5px 0; border-bottom: 1px dashed var(--border-color);
}
.di-mount:last-of-type { border-bottom: none; }
.di-arrow { color: var(--text-muted); }
.di-mount-tag {
  margin-left: auto; font-size: 10.5px; font-weight: 500; flex: none;
  color: var(--text-muted); background: var(--surface-color);
  border: 1px solid var(--border-color); border-radius: 4px; padding: 1px 6px;
}

/* 环境变量（扁平虚线行） */
.di-env-list { list-style: none; margin: 0; padding: 0; }
.di-env-row {
  display: flex; align-items: baseline; gap: 10px;
  font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-color);
}
.di-env-row:last-child { border-bottom: none; }
.di-env-key { color: var(--text-secondary); flex: none; max-width: 45%; word-break: break-all; }
.di-env-val { color: var(--text-primary); word-break: break-all; }
.di-env-val.masked { color: var(--text-muted); letter-spacing: 1px; }
.di-env-reveal { flex: none; height: auto; padding: 0; font-size: 11px; }

/* 标签云（key/value 分色胶囊） */
.di-label-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
.di-label {
  display: inline-flex; max-width: 100%;
  border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden;
  font-size: 11px; background: var(--surface-color);
}
.di-label .di-lk { background: var(--bg-color); color: var(--text-muted); padding: 2px 7px; border-right: 1px solid var(--border-color); }
.di-label .di-lv { color: var(--text-primary); padding: 2px 7px; word-break: break-all; }

.di-empty { color: var(--text-muted); font-size: 12px; padding: 4px 0; }

.exec-tip { margin-top: 10px; font-size: 12px; color: var(--text-muted); }
.exec-tip code {
  font-family: var(--el-font-family-mono, monospace);
  background: var(--surface-color); padding: 1px 5px; border-radius: 4px;
  border: 1px solid var(--border-color);
}


@media (max-width: 768px) {
  .di-kv-grid,
  .di-res-bars,
  .di-net-grid { grid-template-columns: 1fr; }
  .di-env-row { flex-wrap: wrap; gap: 2px 10px; }
}
@media (prefers-reduced-motion: reduce) {
  .di-caret,
  .di-close { transition: none; }
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
