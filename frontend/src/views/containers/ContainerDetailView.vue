<template>
  <main class="cluster-detail">
    <div class="detail-header surface-card">
      <div class="detail-header-copy">
        <div class="detail-title-row">
          <el-button text @click="$router.push('/assets/containers')" aria-label="返回集群列表">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h2 class="page-title detail-title">{{ cluster.name || '集群详情' }}</h2>
          <el-tag :type="statusType(cluster.status)" size="small">
            <span class="tag-dot" :class="cluster.status === 'running' ? 'dot-success' : 'dot-danger'" aria-hidden="true"></span>
            {{ cluster.status === 'running' ? '运行中' : '连接异常' }}
          </el-tag>
          <el-tag v-if="cluster.version" type="info" size="small">{{ cluster.version }}</el-tag>
        </div>
        <div class="detail-meta">
          <span>{{ cluster.description || '未填写说明' }}</span>
          <span class="mono">{{ cluster.endpoint || '-' }}</span>
          <span v-if="lastRefreshAt">
            最后刷新：{{ formatTime(new Date(lastRefreshAt).toISOString()) }}
            <em class="refresh-relative">（{{ lastRefreshText }}）</em>
          </span>
        </div>
      </div>
      <div class="detail-header-actions">
        <div class="auto-refresh-control">
          <span class="auto-refresh-label">自动刷新</span>
          <el-switch
            v-model="autoRefresh"
            inline-prompt
            active-text="30s"
            inactive-text="手动"
            class="auto-refresh-switch"
            aria-label="自动刷新开关"
          />
        </div>
        <el-button :loading="refreshing" size="small" @click="refreshAll" aria-label="刷新集群数据">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button :loading="connectionTesting" size="small" @click="testSavedConnection">
          <el-icon><Connection /></el-icon>
          检测连接
        </el-button>
        <el-button :loading="kubeconfigDownloading" size="small" @click="downloadKubeconfig">
          <el-icon><Download /></el-icon>
          下载 kubeconfig
        </el-button>
        <el-button size="small" @click="openEditDialog">
          <el-icon><EditPen /></el-icon>
          编辑
        </el-button>
        <el-button type="danger" size="small" plain @click="confirmDeleteCluster">删除</el-button>
      </div>
    </div>

    <div v-if="clusterError" class="error-banner">
      <span class="error-banner-text">集群信息加载失败：{{ clusterError }}</span>
      <el-button size="small" @click="fetchCluster">重试</el-button>
    </div>

    <div v-if="resourcesError && !initialLoading" class="error-banner">
      <span class="error-banner-text">资源数据加载失败：{{ resourcesError }}</span>
      <el-button size="small" @click="refreshAll">重试</el-button>
    </div>

    <div v-if="anomalyList.length" class="warning-banner" role="alert">
      <span>当前建议优先处理：{{ anomalyList[0]?.text }}{{ anomalyList[1] ? `，${anomalyList[1].text}` : '' }}。</span>
      <span class="warning-meta">异常优先 · 数据每 30s 同步</span>
    </div>

    <div class="summary-grid" role="region" aria-label="集群资源概览">
      <template v-if="initialLoading">
        <div v-for="i in 4" :key="i" class="summary-card surface-card"><el-skeleton :rows="2" animated /></div>
      </template>
      <template v-else>
        <button type="button" class="summary-card surface-card clickable" @click="gotoTab('nodes')" aria-label="查看节点资源">
          <div class="summary-label">节点<span class="go-link">点击查看 ›</span></div>
          <div class="summary-value">
            {{ resources.ready_nodes ?? resources.node_count ?? 0 }}
            <span class="sub">/ {{ resources.node_count ?? 0 }} Ready</span>
          </div>
          <div class="summary-foot" :class="{ 'text-warning': resourceSummary.notReadyNodeCount > 0 }">
            {{ resourceSummary.notReadyNodeCount > 0 ? `${resourceSummary.notReadyNodeCount} 个节点未就绪` : '节点状态正常' }}
          </div>
        </button>
        <button type="button" class="summary-card surface-card clickable" @click="gotoTab('pods', 'abnormal')" aria-label="查看异常 Pod">
          <div class="summary-label">Pods<span class="go-link">点击看异常 ›</span></div>
          <div class="summary-value">
            {{ resources.pod_count ?? 0 }}
            <span class="sub" :class="{ 'text-danger': resourceSummary.abnormalPodCount > 0 }">· {{ resourceSummary.abnormalPodCount }} 异常</span>
          </div>
          <div class="summary-foot">
            CrashLoop {{ podFilterCounts.crash }} · Pending {{ podFilterCounts.pending }} · OOM {{ podFilterCounts.oom }}
          </div>
        </button>
        <button type="button" class="summary-card surface-card clickable" @click="gotoTab('nodes')" aria-label="查看 CPU 资源申请情况">
          <div class="summary-label">CPU 申请率</div>
          <div class="summary-value" :class="allocTextClass(clusterAlloc.cpuPercent)">{{ clusterAlloc.cpuPercent }}%</div>
          <div class="progress" :class="allocLevel(clusterAlloc.cpuPercent)">
            <i :style="{ width: Math.min(clusterAlloc.cpuPercent, 100) + '%' }"></i>
          </div>
          <div class="progress-note">
            <span>已申请 {{ clusterAlloc.cpuRequest.toFixed(1) }} 核</span>
            <span>共 {{ clusterAlloc.cpuCapacity }} 核</span>
          </div>
        </button>
        <button type="button" class="summary-card surface-card clickable" @click="gotoTab('nodes')" aria-label="查看内存资源申请情况">
          <div class="summary-label">内存申请率</div>
          <div class="summary-value" :class="allocTextClass(clusterAlloc.memPercent)">{{ clusterAlloc.memPercent }}%</div>
          <div class="progress" :class="allocLevel(clusterAlloc.memPercent)">
            <i :style="{ width: Math.min(clusterAlloc.memPercent, 100) + '%' }"></i>
          </div>
          <div class="progress-note">
            <span>已申请 {{ fmtGi(clusterAlloc.memRequestMi) }}</span>
            <span>共 {{ fmtGi(clusterAlloc.memCapacityMi) }}</span>
          </div>
        </button>
      </template>
    </div>

    <div class="workbench-grid">
      <section class="surface-card workbench-main" v-loading="refreshing && !initialLoading">
        <div class="tabs-row" role="tablist">
          <button
            v-for="item in visibleTabs"
            :key="item.value"
            type="button"
            class="tab-button"
            :class="{ active: activeTab === item.value }"
            role="tab"
            :aria-selected="activeTab === item.value"
            @click="gotoTab(item.value)"
          >
            {{ item.label }}
            <span v-if="item.badge" class="tab-badge" :class="item.type">{{ item.badge }}</span>
          </button>
        </div>

        <div v-if="activeTab === 'pods'" class="section-body">
          <div class="tool-row">
            <el-select v-model="podNamespace" placeholder="全部命名空间" clearable class="tool-select" aria-label="按命名空间筛选">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="podSearch" placeholder="搜索 Pod / 状态 / 节点" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredPods.length }} 个 Pod</span>
          </div>
          <div class="chip-row">
            <button
              v-for="chip in podChips"
              :key="chip.value"
              type="button"
              class="chip"
              :class="{ active: podFilter === chip.value, danger: chip.value === 'abnormal' }"
              @click="setPodFilter(chip.value)"
            >
              {{ chip.label }}<template v-if="chip.count !== undefined"> ({{ chip.count }})</template>
            </button>
          </div>
          <div v-if="deployFilter" class="filter-banner">
            <span><el-icon><Link /></el-icon>正在查看 Deployment「<b>{{ deployFilter }}</b>」的 Pods</span>
            <el-button link type="primary" size="small" @click="clearDeployFilter"><el-icon><Close /></el-icon>清除筛选</el-button>
          </div>

          <div class="table-wrapper">
            <el-table :data="pagedPods" stripe empty-text="暂无 Pod 数据" aria-label="Pod 列表">
              <el-table-column label="Pod" min-width="240">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.namespace || '-' }} · {{ row.pod_ip || row.node || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="130" align="center">
                <template #default="{ row }">
                  <el-tag :type="podStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="原因" min-width="150" align="center" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tooltip v-if="row.reason || row.message" :content="row.message || row.reason" placement="top">
                    <el-tag :type="podReasonType(row.reason || row.status)" size="small" effect="plain">
                      {{ row.reason || '-' }}
                    </el-tag>
                  </el-tooltip>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="node" label="节点" width="130" align="center" show-overflow-tooltip />
              <el-table-column label="重启" width="90" align="center">
                <template #header>
                  <button type="button" class="sort-header" @click="toggleRestartsOrder" aria-label="按重启次数排序">
                    重启
                    <el-icon v-if="restartsOrder === 'asc'"><CaretTop /></el-icon>
                    <el-icon v-else-if="restartsOrder === 'desc'"><CaretBottom /></el-icon>
                    <el-icon v-else class="sort-idle"><DCaret /></el-icon>
                  </button>
                </template>
                <template #default="{ row }">
                  <span :class="{ 'text-danger restarts-strong': (row.restarts ?? 0) > 5 }">{{ row.restarts }}</span>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" width="150" align="center">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="150" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openPodDrawer(row, 'logs')">日志</el-button>
                  <el-button link type="info" size="small" @click="openPodDrawer(row, 'events')">事件</el-button>
                  <el-button link type="danger" size="small" @click="confirmDeletePod(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="podPage"
              v-model:page-size="podPageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="filteredPods.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>

        <div v-else-if="activeTab === 'deployments'" class="section-body">
          <div class="tool-row">
            <el-select v-model="depNamespace" placeholder="全部命名空间" clearable class="tool-select">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="depSearch" placeholder="搜索 Deployment" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredDeployments.length }} 个 Deployment</span>
          </div>
          <el-alert type="info" :closable="false" class="pane-tip">点击行可下钻查看该 Deployment 的 Pods。</el-alert>

          <div class="table-wrapper">
            <el-table :data="pagedDeployments" stripe empty-text="暂无 Deployment 数据" aria-label="Deployment 列表" @row-click="drilldownDeployment" class="clickable-rows">
              <el-table-column label="Deployment" min-width="230">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.namespace || '-' }} · {{ (row.images || []).join(', ') || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="depStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="副本" width="100" align="center">
                <template #default="{ row }">
                  <span :class="{ 'text-warning': row.ready_replicas < row.replicas }">{{ row.ready_replicas }} / {{ row.replicas }}</span>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" width="160" align="center">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click.stop="drilldownDeployment(row)">Pods</el-button>
                  <el-button link type="warning" size="small" @click.stop="confirmRestartDeployment(row)">重启</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="depPage"
              v-model:page-size="depPageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredDeployments.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>

        <div v-else-if="activeTab === 'nodes'" class="section-body">
          <div class="table-wrapper">
            <el-table :data="pagedNodes" stripe aria-label="节点列表">
              <el-table-column label="节点" min-width="200">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.ip || '-' }} · {{ row.os_image || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100" align="center">
                <template #default="{ row }">
                  <div class="node-status-cell">
                    <el-tag :type="row.status === 'Ready' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
                    <el-tag v-if="row.unschedulable" type="warning" size="small" effect="plain">已封锁</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="CPU 申请" width="170" align="center">
                <template #default="{ row }">
                  <div class="alloc-cell">
                    <div class="progress" :class="allocLevel(nodeAlloc(row.name).cpuPercent)">
                      <i :style="{ width: Math.min(nodeAlloc(row.name).cpuPercent, 100) + '%' }"></i>
                    </div>
                    <div class="progress-note">
                      <span>{{ nodeAlloc(row.name).cpuPercent }}%</span>
                      <span>{{ nodeAlloc(row.name).cpuRequest.toFixed(1) }}/{{ row.cpu || 0 }} 核</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="内存申请" width="170" align="center">
                <template #default="{ row }">
                  <div class="alloc-cell">
                    <div class="progress" :class="allocLevel(nodeAlloc(row.name).memPercent)">
                      <i :style="{ width: Math.min(nodeAlloc(row.name).memPercent, 100) + '%' }"></i>
                    </div>
                    <div class="progress-note">
                      <span>{{ nodeAlloc(row.name).memPercent }}%</span>
                      <span>{{ fmtGi(nodeAlloc(row.name).memRequestMi) }}/{{ formatMemory(row.memory || '') }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="Pods" width="80" align="center">
                <template #default="{ row }">{{ podsOnNode(row.name) }}</template>
              </el-table-column>
              <el-table-column prop="container_runtime" label="容器运行时" min-width="160" align="center" show-overflow-tooltip />
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openNodeDetail(row)">详情</el-button>
                  <el-button link type="warning" size="small" @click="openMaintenanceDialog(row)">维护</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="nodePage"
              v-model:page-size="nodePageSize"
              :page-sizes="[10, 20, 50]"
              :total="(resources.nodes || []).length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>

        <div v-else-if="activeTab === 'namespaces'" class="section-body">
          <div class="table-wrapper">
            <el-table :data="pagedNamespaces" stripe aria-label="命名空间列表">
              <el-table-column label="命名空间" min-width="200">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>Pods {{ row.pods }} · Deployments {{ row.deployments }} · Services {{ row.services }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="abnormal_pods" label="异常 Pods" width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.abnormal_pods > 0 ? 'warning' : 'success'" size="small">{{ row.abnormal_pods }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="资源热度" width="200" align="center">
                <template #default="{ row }">
                  <div class="alloc-cell">
                    <div class="progress" :class="allocLevel(nsHeatPercent(row.name))">
                      <i :style="{ width: Math.min(nsHeatPercent(row.name), 100) + '%' }"></i>
                    </div>
                    <div class="progress-note"><span>{{ nsHeatPercent(row.name) }}%</span><span>内存申请占比</span></div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openNamespaceDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="nsPage"
              v-model:page-size="nsPageSize"
              :page-sizes="[10, 20, 50]"
              :total="(resources.namespace_overview || []).length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>

        <div v-else-if="activeTab === 'services'" class="section-body">
          <div class="tool-row">
            <el-select v-model="svcNamespace" placeholder="全部命名空间" clearable class="tool-select">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="svcSearch" placeholder="搜索 Service" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredServices.length }} 个 Service</span>
          </div>

          <div class="table-wrapper">
            <el-table :data="pagedServices" stripe empty-text="暂无 Service 数据" aria-label="Service 列表">
              <el-table-column label="Service" min-width="220">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.namespace || '-' }} · {{ row.service_type || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="cluster_ip" label="Cluster IP" width="140" align="center" />
              <el-table-column prop="ports" label="端口" min-width="180" align="center" show-overflow-tooltip />
              <el-table-column label="操作" width="80" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openServiceDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="svcPage"
              v-model:page-size="svcPageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredServices.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>

        <div v-else class="section-body">
          <div class="tool-row">
            <el-select v-model="eventType" placeholder="全部级别" clearable class="tool-select-sm" aria-label="按事件级别筛选">
              <el-option label="Warning" value="Warning" />
              <el-option label="Normal" value="Normal" />
            </el-select>
            <el-select v-model="eventNs" placeholder="全部命名空间" clearable class="tool-select">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="eventSearch" placeholder="搜索原因 / 对象 / 消息" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredEvents.length }} 条 · Warning {{ warningEventCount }}</span>
          </div>

          <div v-loading="clusterEventsLoading" class="event-list">
            <div v-for="(ev, idx) in pagedEvents" :key="idx" class="event-item">
              <i class="event-dot" :class="eventDotClass(ev.type)" aria-hidden="true"></i>
              <div class="event-body">
                <strong>{{ ev.reason || '-' }} · {{ ev.involved_kind }}/{{ ev.involved_name }}</strong>
                <p>{{ ev.message || '-' }}</p>
                <span class="event-sub">{{ ev.namespace || '-' }} · {{ ev.source || '-' }} · ×{{ ev.count ?? 1 }}</span>
              </div>
              <span class="event-time">{{ formatTime(ev.last_timestamp) }}</span>
            </div>
            <el-empty v-if="!clusterEventsLoading && !pagedEvents.length" description="暂无事件" :image-size="60" />
          </div>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="evPage"
              v-model:page-size="evPageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredEvents.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>
      </section>

      <aside class="workbench-side">
        <div v-if="rootCauseChain.length" class="surface-card side-card">
          <div class="side-card-head">
            <h3><el-icon><Connection /></el-icon>排查链路</h3>
            <span class="side-card-subtitle">异常关联推断 · 从根因到影响面</span>
          </div>
          <div class="rc-chain">
            <button
              v-for="(item, idx) in rootCauseChain"
              :key="idx"
              type="button"
              class="rc-node"
              :class="item.level"
              @click="gotoTab(item.tab, item.filter)"
            >
              <span class="rc-tag">{{ item.level === 'root' ? '根因疑似' : '影响' }}</span>
              <strong>{{ item.title }}</strong>
              <span>{{ item.desc }}</span>
            </button>
          </div>
        </div>

        <div class="surface-card side-card">
          <div class="side-card-head">
            <h3>当前异常</h3>
            <span class="side-card-subtitle">点击可跳转并自动套用筛选</span>
          </div>
          <div class="side-list">
            <button v-for="item in sideHighlights" :key="item.key" type="button" class="side-item clickable" @click="onAnomalyClick(item.key)">
              <div class="side-item-top">
                <strong>{{ item.text }}</strong>
                <el-tag :type="item.key === 'pods' ? 'danger' : 'warning'" size="small">{{ item.count }}</el-tag>
              </div>
              <span>{{ sideHint(item.key) }}</span>
            </button>
            <div v-if="!sideHighlights.length" class="side-item">
              <div class="side-item-top">
                <strong>未发现明显异常</strong>
              </div>
              <span>可以继续查看 Pods、Deployments 或命名空间的实时状态。</span>
            </div>
          </div>
        </div>

        <div class="surface-card side-card">
          <div class="side-card-head">
            <h3>命名空间热区</h3>
            <span class="side-card-subtitle">按内存申请占比排序</span>
          </div>
          <div class="ns-heat-list">
            <div v-for="item in topNsHeat" :key="item.name" class="ns-bar-row">
              <span class="ns-name" :title="item.name">{{ item.name }}</span>
              <div class="progress" :class="allocLevel(item.percent)"><i :style="{ width: Math.min(item.percent, 100) + '%' }"></i></div>
              <b>{{ item.percent }}%</b>
            </div>
            <span v-if="!topNsHeat.length" class="side-card-subtitle">等待资源同步</span>
          </div>
        </div>

        <div class="surface-card side-card quick-actions-card">
          <div class="side-card-head">
            <h3><el-icon><Tools /></el-icon>快捷操作</h3>
            <span class="side-card-subtitle">常用运维入口</span>
          </div>
          <div class="quick-actions-list">
            <button type="button" class="quick-action" :disabled="kubeconfigDownloading" @click="downloadKubeconfig">
              <el-icon><Download /></el-icon>
              <span><strong>下载 kubeconfig</strong><small>供本地 kubectl 排障使用</small></span>
            </button>
            <button type="button" class="quick-action" :disabled="connectionTesting" @click="testSavedConnection">
              <el-icon><Connection /></el-icon>
              <span><strong>重新检测连接</strong><small>验证 API Server 与保存的 Token</small></span>
            </button>
            <button type="button" class="quick-action quick-action-warning" @click="openMaintenanceDialog()">
              <el-icon><WarningFilled /></el-icon>
              <span><strong>节点维护模式</strong><small>先预检，再执行 Cordon 或 Drain</small></span>
            </button>
          </div>
        </div>
      </aside>
    </div>

    <el-drawer v-model="drawerVisible" size="680px" :with-header="false" destroy-on-close>
      <div class="drawer-head">
        <div class="drawer-head-copy">
          <h3>{{ selectedPod?.name || 'Pod' }}</h3>
          <div class="drawer-sub">{{ selectedPod?.namespace || '-' }} · {{ selectedPod?.node || '-' }}</div>
        </div>
        <div v-if="drawerTab === 'logs'" class="drawer-actions">
          <el-button size="small" @click="copyLogs">复制</el-button>
          <el-button size="small" @click="downloadLogs">下载</el-button>
        </div>
      </div>
      <div class="tabs-row drawer-tabs" role="tablist">
        <button type="button" class="tab-button" :class="{ active: drawerTab === 'logs' }" @click="drawerTab = 'logs'">日志</button>
        <button type="button" class="tab-button" :class="{ active: drawerTab === 'events' }" @click="drawerTab = 'events'">事件</button>
      </div>
      <div class="drawer-body">
        <div v-if="drawerTab === 'logs'" v-loading="logsLoading">
          <pre class="log-box" tabindex="0" role="log" aria-label="Pod 日志">{{ podLogs || '暂无日志' }}</pre>
        </div>
        <div v-else v-loading="eventsLoading">
          <el-table :data="pagedPodEvents" stripe empty-text="暂无事件" aria-label="Pod 事件列表">
            <el-table-column prop="type" label="类型" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.type === 'Warning' ? 'warning' : 'info'" size="small">{{ row.type || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" width="140" show-overflow-tooltip />
            <el-table-column prop="message" label="消息" min-width="240" show-overflow-tooltip />
            <el-table-column prop="count" label="次数" width="70" align="center" />
            <el-table-column prop="last_timestamp" label="最后时间" width="160" align="center">
              <template #default="{ row }">{{ formatTime(row.last_timestamp) }}</template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap" v-if="podEvents.length > 10">
            <el-pagination
              v-model:current-page="eventPage"
              v-model:page-size="eventPageSize"
              :page-sizes="[10, 20, 50]"
              :total="podEvents.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="svcDetailVisible" :title="svcDialogTitle" width="600px">
      <el-descriptions v-if="selectedService" :column="1" border>
        <el-descriptions-item label="名称">{{ selectedService.name }}</el-descriptions-item>
        <el-descriptions-item label="命名空间">{{ selectedService.namespace }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ selectedService.service_type }}</el-descriptions-item>
        <el-descriptions-item label="Cluster IP">{{ selectedService.cluster_ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ selectedService.ports || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Selector">{{ selectedService.selector || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(selectedService.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="nodeDetailVisible" :title="nodeDialogTitle" width="600px">
      <el-descriptions v-if="selectedNode" :column="1" border>
        <el-descriptions-item label="节点名称">{{ selectedNode.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="selectedNode.status === 'Ready' ? 'success' : 'danger'" size="small">{{ selectedNode.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="IP">{{ selectedNode.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="CPU">{{ selectedNode.cpu ? selectedNode.cpu + ' 核' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="内存">{{ formatMemory(selectedNode.memory || '') }}</el-descriptions-item>
        <el-descriptions-item label="kubelet">{{ selectedNode.kubelet_version || '-' }}</el-descriptions-item>
        <el-descriptions-item label="系统">{{ selectedNode.os_image || '-' }}</el-descriptions-item>
        <el-descriptions-item label="容器运行时">{{ selectedNode.container_runtime || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="nsDetailVisible" :title="nsDialogTitle" width="500px">
      <el-descriptions v-if="selectedNamespace" :column="1" border>
        <el-descriptions-item label="命名空间">{{ selectedNamespace.name }}</el-descriptions-item>
        <el-descriptions-item label="Pods">{{ selectedNamespace.pods }}</el-descriptions-item>
        <el-descriptions-item label="异常 Pods">
          <el-tag :type="selectedNamespace.abnormal_pods > 0 ? 'warning' : 'success'" size="small">{{ selectedNamespace.abnormal_pods }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Deployments">{{ selectedNamespace.deployments }}</el-descriptions-item>
        <el-descriptions-item label="Services">{{ selectedNamespace.services }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑 K8s 集群" width="min(600px, 92vw)" destroy-on-close>
      <el-alert type="info" :closable="false" class="dialog-notice">
        Token 留空将继续使用已保存的凭证；保存前会校验新的连接配置。
      </el-alert>
      <el-form ref="clusterFormRef" :model="clusterForm" :rules="clusterRules" label-position="top" class="cluster-edit-form">
        <el-form-item label="集群名称" prop="name">
          <el-input v-model="clusterForm.name" placeholder="例：prod-k8s" />
        </el-form-item>
        <el-form-item label="API Server" prop="endpoint">
          <el-input v-model="clusterForm.endpoint" placeholder="例：https://10.0.0.1:6443" />
        </el-form-item>
        <el-form-item label="ServiceAccount Token">
          <el-input v-model="clusterForm.token" type="textarea" :rows="4" placeholder="留空以保留原 Token" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="clusterForm.description" placeholder="集群用途、环境或值班说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="clusterSaving" @click="saveCluster">保存并验证</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="maintenanceVisible" title="节点维护模式" width="min(680px, 92vw)" destroy-on-close @closed="resetMaintenanceState">
      <div class="maintenance-dialog">
        <el-alert type="warning" :closable="false" class="dialog-notice">
          Drain 仅会提交已通过预检的 Pod 驱逐请求。静态 Pod、DaemonSet 不会被驱逐；未受控制器管理或使用 emptyDir 的 Pod 会阻止执行。
        </el-alert>
        <el-form label-position="top">
          <el-form-item label="目标节点">
            <el-select v-model="maintenanceNodeName" placeholder="选择需要维护的节点" filterable class="maintenance-node-select" @change="loadMaintenancePreview">
              <el-option v-for="node in nodes" :key="node.name" :label="node.name" :value="node.name">
                <span>{{ node.name }}</span>
                <span class="node-option-meta">{{ node.status }}{{ node.unschedulable ? ' · 已封锁' : '' }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-form>

        <div v-if="maintenancePreview" v-loading="maintenancePreviewLoading" class="maintenance-preview" aria-live="polite">
          <div class="maintenance-summary">
            <span>节点上的 Pod：<b>{{ maintenancePreview.pod_count }}</b></span>
            <span>可驱逐：<b>{{ maintenancePreview.evictable.length }}</b></span>
            <span :class="{ 'text-warning': maintenancePreview.skipped.length }">跳过：<b>{{ maintenancePreview.skipped.length }}</b></span>
            <span :class="{ 'text-danger': maintenancePreview.blocked.length }">阻塞：<b>{{ maintenancePreview.blocked.length }}</b></span>
          </div>
          <div class="maintenance-list-grid">
            <section v-if="maintenancePreview.evictable.length" class="maintenance-list-section">
              <h4>可驱逐</h4>
              <p v-for="item in maintenancePreview.evictable" :key="`evictable-${item.namespace}-${item.name}`">{{ item.namespace }}/{{ item.name }}</p>
            </section>
            <section v-if="maintenancePreview.skipped.length" class="maintenance-list-section">
              <h4>跳过</h4>
              <p v-for="item in maintenancePreview.skipped" :key="`skipped-${item.namespace}-${item.name}`">{{ item.namespace }}/{{ item.name }}<small>{{ item.reason }}</small></p>
            </section>
            <section v-if="maintenancePreview.blocked.length" class="maintenance-list-section is-blocked">
              <h4>需人工处理</h4>
              <p v-for="item in maintenancePreview.blocked" :key="`blocked-${item.namespace}-${item.name}`">{{ item.namespace }}/{{ item.name }}<small>{{ item.reason }}</small></p>
            </section>
          </div>
        </div>
        <el-empty v-else-if="maintenanceNodeName && !maintenancePreviewLoading" description="暂未获取到预检结果" :image-size="54" />

        <el-form v-if="maintenanceNodeName" label-position="top" class="maintenance-confirm-form">
          <el-form-item :label="`输入 ${maintenanceNodeName} 以确认维护操作`">
            <el-input v-model="maintenanceConfirmNode" :placeholder="maintenanceNodeName" autocomplete="off" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="maintenanceVisible = false">取消</el-button>
        <el-button
          v-if="maintenancePreview?.node.unschedulable"
          :disabled="!maintenanceActionReady"
          :loading="maintenanceSubmitting"
          @click="restoreNodeScheduling"
        >恢复调度</el-button>
        <el-button
          v-else
          type="warning"
          :disabled="!maintenanceActionReady"
          :loading="maintenanceSubmitting"
          @click="cordonNode"
        >仅 Cordon</el-button>
        <el-button
          type="danger"
          :disabled="!maintenanceActionReady || !!maintenancePreview?.blocked.length"
          :loading="maintenanceSubmitting"
          @click="drainNode"
        >执行 Drain</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  ArrowLeft,
  CaretBottom,
  CaretTop,
  Close,
  Connection,
  DCaret,
  Download,
  EditPen,
  Link,
  Refresh,
  Tools,
  WarningFilled,
} from '@element-plus/icons-vue'
import {
  cordonClusterNode,
  deleteCluster,
  deleteClusterPod,
  downloadClusterKubeconfig,
  drainClusterNode,
  getCluster,
  getClusterEvents,
  getClusterResources,
  getNodeMaintenancePreview,
  getPodEvents,
  getPodLogs,
  restartClusterDeployment,
  testSavedClusterConnection,
  updateCluster,
} from '@/api/containers'
import {
  buildClusterAnomalies,
  computeAllocation,
  filterClusterPods,
  matchPodQuickFilter,
  summarizeClusterResources,
  type PodQuickFilter,
  type ResourceAllocation,
} from '@/utils/k8sCluster'

interface K8sPod {
  name: string
  namespace: string
  status: string
  reason?: string
  message?: string
  node?: string
  pod_ip?: string
  images?: string[]
  restarts?: number
  cpu_request?: number
  mem_request?: number
  created_at?: string
}

interface K8sNode {
  name: string
  status: string
  unschedulable?: boolean
  ip?: string
  cpu?: string | number
  memory?: string
  kubelet_version?: string
  os_image?: string
  container_runtime?: string
}

interface MaintenancePod {
  name: string
  namespace: string
  reason: string
}

interface MaintenancePreview {
  node: K8sNode
  pod_count: number
  evictable: MaintenancePod[]
  skipped: MaintenancePod[]
  blocked: MaintenancePod[]
}

interface K8sDeployment {
  name: string
  namespace: string
  status: string
  images?: string[]
  replicas: number
  ready_replicas: number
  created_at?: string
}

interface K8sService {
  name: string
  namespace: string
  service_type: string
  cluster_ip?: string
  ports?: string
  selector?: string
  created_at?: string
}

interface K8sNamespace {
  name: string
  pods: number
  abnormal_pods: number
  deployments: number
  services: number
}

interface ClusterEvent {
  type?: string
  reason?: string
  message?: string
  count?: number
  source?: string
  namespace?: string
  involved_kind?: string
  involved_name?: string
  last_timestamp?: string
}

interface K8sResources {
  connected?: boolean
  error?: string
  version?: string
  node_count?: number
  ready_nodes?: number
  pod_count?: number
  deployment_count?: number
  service_count?: number
  namespace_count?: number
  namespaces?: string[]
  namespace_overview?: K8sNamespace[]
  nodes?: K8sNode[]
  pods?: K8sPod[]
  deployments?: K8sDeployment[]
  services?: K8sService[]
}

interface PodEvent {
  type?: string
  reason?: string
  message?: string
  count?: number
  source?: string
  last_timestamp?: string
}

const route = useRoute()
const router = useRouter()
const clusterName = computed(() => (
  route.name === 'ContainerDetail' ? String(route.params.name ?? '') : ''
))

const cluster = ref<Record<string, any>>({})
const resources = ref<K8sResources>({})
const refreshing = ref(false)
const initialLoading = ref(true)
const clusterError = ref('')
const resourcesError = ref('')
const editVisible = ref(false)
const clusterSaving = ref(false)
const connectionTesting = ref(false)
const kubeconfigDownloading = ref(false)
const clusterFormRef = ref<FormInstance>()
const clusterForm = reactive({
  name: '',
  endpoint: '',
  token: '',
  description: '',
})
const clusterRules = {
  name: [{ required: true, message: '请输入集群名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 API Server 地址', trigger: 'blur' }],
}

const autoRefresh = ref(true)
const lastRefreshAt = ref(0)
const nowTick = ref(Date.now())

const activeTab = ref((route.query.tab as string) || 'pods')
const podFilter = ref<PodQuickFilter>((route.query.pf as PodQuickFilter) || 'all')
const deployFilter = ref('')
const restartsOrder = ref<'' | 'asc' | 'desc'>('')
const nsPage = ref(Number(route.query.nsp) || 1)
const nsPageSize = ref(Number(route.query.nss) || 10)
const nodePage = ref(Number(route.query.ndp) || 1)
const nodePageSize = ref(Number(route.query.nds) || 10)
const podPage = ref(Number(route.query.pp) || 1)
const podPageSize = ref(Number(route.query.ps) || 10)
const depPage = ref(Number(route.query.dp) || 1)
const depPageSize = ref(Number(route.query.ds) || 10)
const svcPage = ref(Number(route.query.sp) || 1)
const svcPageSize = ref(Number(route.query.ss) || 10)

function syncUrl() {
  router.replace({
    query: {
      ...route.query,
      tab: activeTab.value,
      pf: podFilter.value,
      nsp: String(nsPage.value), nss: String(nsPageSize.value),
      ndp: String(nodePage.value), nds: String(nodePageSize.value),
      pp: String(podPage.value), ps: String(podPageSize.value),
      dp: String(depPage.value), ds: String(depPageSize.value),
      sp: String(svcPage.value), ss: String(svcPageSize.value),
    },
  })
}

watch(activeTab, syncUrl)
watch(podFilter, syncUrl)
watch([nsPage, nsPageSize], syncUrl)
watch([nodePage, nodePageSize], syncUrl)
watch([podPage, podPageSize], syncUrl)
watch([depPage, depPageSize], syncUrl)
watch([svcPage, svcPageSize], syncUrl)
watch(() => route.query.tab, (value) => {
  if (value && typeof value === 'string') activeTab.value = value
})

const selectedPod = ref<K8sPod | null>(null)
const drawerVisible = ref(false)
const drawerTab = ref<'logs' | 'events'>('logs')
const logsLoading = ref(false)
const eventsLoading = ref(false)
const podLogs = ref('')
const podEvents = ref<PodEvent[]>([])
const eventPage = ref(1)
const eventPageSize = ref(10)

const clusterEvents = ref<ClusterEvent[]>([])
const clusterEventsLoading = ref(false)
const eventType = ref('')
const eventNs = ref('')
const eventSearch = ref('')
const evPage = ref(1)
const evPageSize = ref(10)

const svcDetailVisible = ref(false)
const selectedService = ref<K8sService | null>(null)
const svcDialogTitle = computed(() => selectedService.value ? `Service: ${selectedService.value.name}` : 'Service 详情')

const nodeDetailVisible = ref(false)
const selectedNode = ref<K8sNode | null>(null)
const nodeDialogTitle = computed(() => selectedNode.value ? `节点: ${selectedNode.value.name}` : '节点详情')

const maintenanceVisible = ref(false)
const maintenanceNodeName = ref('')
const maintenancePreview = ref<MaintenancePreview | null>(null)
const maintenancePreviewLoading = ref(false)
const maintenanceSubmitting = ref(false)
const maintenanceConfirmNode = ref('')
const maintenanceConfirmed = computed(() => (
  Boolean(maintenanceNodeName.value) && maintenanceConfirmNode.value.trim() === maintenanceNodeName.value
))
const maintenanceActionReady = computed(() => (
  maintenanceConfirmed.value && !maintenancePreviewLoading.value && Boolean(maintenancePreview.value)
))

const nsDetailVisible = ref(false)
const selectedNamespace = ref<K8sNamespace | null>(null)
const nsDialogTitle = computed(() => selectedNamespace.value ? `命名空间: ${selectedNamespace.value.name}` : '命名空间详情')

const podNamespace = ref('')
const podSearch = ref('')
const depNamespace = ref('')
const depSearch = ref('')
const svcNamespace = ref('')
const svcSearch = ref('')

const pods = computed(() => resources.value.pods || [])
const nodes = computed(() => resources.value.nodes || [])

const anomalyList = computed(() => buildClusterAnomalies(resources.value))
const resourceSummary = computed(() => summarizeClusterResources(resources.value))
const sideHighlights = computed(() => anomalyList.value.slice(0, 3))

const clusterAlloc = computed(() => computeAllocation(nodes.value, pods.value))

const nodeAllocMap = computed(() => {
  const map = new Map<string, ResourceAllocation>()
  for (const node of nodes.value) {
    map.set(node.name, computeAllocation([node], pods.value.filter((p) => p.node === node.name)))
  }
  return map
})
const EMPTY_ALLOC: ResourceAllocation = { cpuRequest: 0, cpuCapacity: 0, cpuPercent: 0, memRequestMi: 0, memCapacityMi: 0, memPercent: 0 }
function nodeAlloc(name: string): ResourceAllocation {
  return nodeAllocMap.value.get(name) || EMPTY_ALLOC
}
function podsOnNode(name: string) {
  return pods.value.filter((p) => p.node === name).length
}

const nsHeat = computed(() => {
  const byNs = new Map<string, number>()
  let total = 0
  for (const p of pods.value) {
    const mi = p.mem_request ?? 0
    byNs.set(p.namespace, (byNs.get(p.namespace) || 0) + mi)
    total += mi
  }
  return { byNs, total }
})
const topNsHeat = computed(() => {
  const total = nsHeat.value.total
  return [...nsHeat.value.byNs.entries()]
    .map(([name, mi]) => ({ name, percent: total ? Math.round((mi / total) * 100) : 0 }))
    .sort((a, b) => b.percent - a.percent)
    .slice(0, 4)
})
function nsHeatPercent(ns: string) {
  const total = nsHeat.value.total
  return total ? Math.round(((nsHeat.value.byNs.get(ns) || 0) / total) * 100) : 0
}

const podFilterCounts = computed(() => ({
  abnormal: pods.value.filter((p) => matchPodQuickFilter(p, 'abnormal')).length,
  crash: pods.value.filter((p) => matchPodQuickFilter(p, 'crash')).length,
  pending: pods.value.filter((p) => matchPodQuickFilter(p, 'pending')).length,
  oom: pods.value.filter((p) => matchPodQuickFilter(p, 'oom')).length,
  restarts: pods.value.filter((p) => matchPodQuickFilter(p, 'restarts')).length,
}))

const podChips = computed(() => [
  { label: '全部', value: 'all' as PodQuickFilter, count: undefined as number | undefined },
  { label: '只看异常', value: 'abnormal' as PodQuickFilter, count: podFilterCounts.value.abnormal },
  { label: 'CrashLoopBackOff', value: 'crash' as PodQuickFilter, count: podFilterCounts.value.crash },
  { label: 'Pending', value: 'pending' as PodQuickFilter, count: podFilterCounts.value.pending },
  { label: 'OOMKilled', value: 'oom' as PodQuickFilter, count: podFilterCounts.value.oom },
  { label: '重启 > 5 次', value: 'restarts' as PodQuickFilter, count: podFilterCounts.value.restarts },
])

const warningEventCount = computed(() => clusterEvents.value.filter((e) => e.type === 'Warning').length)

const visibleTabs = computed(() => [
  { label: 'Pods', value: 'pods', badge: resourceSummary.value.abnormalPodCount, type: 'danger' },
  { label: 'Deployments', value: 'deployments', badge: 0, type: '' },
  { label: '节点', value: 'nodes', badge: resourceSummary.value.notReadyNodeCount, type: 'warning' },
  { label: '命名空间', value: 'namespaces', badge: 0, type: '' },
  { label: 'Services', value: 'services', badge: 0, type: '' },
  { label: '事件', value: 'events', badge: warningEventCount.value, type: 'warning' },
])

const rootCauseChain = computed(() => {
  const items: { level: 'root' | 'mid'; title: string; desc: string; tab: string; filter?: PodQuickFilter }[] = []
  const pressured = nodes.value.filter((n) => n.status !== 'Ready' || nodeAlloc(n.name).memPercent >= 85)
  const crashing = pods.value.filter((p) => matchPodQuickFilter(p, 'crash'))
  const pending = pods.value.filter((p) => p.status === 'Pending')

  if (pressured.length) {
    const node = pressured[0]
    const alloc = nodeAlloc(node.name)
    const reason = node.status !== 'Ready' ? '未就绪' : `内存申请率 ${alloc.memPercent}%`
    items.push({ level: 'root', title: `${node.name} ${reason}`, desc: '节点异常通常会同时影响调度与其上的工作负载', tab: 'nodes' })
    const onNode = crashing.filter((p) => p.node === node.name)
    if (onNode.length) {
      items.push({ level: 'mid', title: `${onNode.length} 个 Pod 在该节点上持续崩溃`, desc: onNode.slice(0, 2).map((p) => p.name).join('、'), tab: 'pods', filter: 'crash' })
    }
  } else if (crashing.length) {
    items.push({ level: 'root', title: `${crashing.length} 个 Pod 持续崩溃`, desc: crashing[0]?.name || '', tab: 'pods', filter: 'crash' })
  }
  if (pending.length) {
    items.push({ level: 'mid', title: `${pending.length} 个 Pod 调度失败`, desc: pending[0]?.message || '资源不足或亲和性不满足', tab: 'pods', filter: 'pending' })
  }
  return items.slice(0, 3)
})

const filteredPods = computed(() => {
  let list = pods.value
  if (deployFilter.value) list = list.filter((p) => p.name.startsWith(deployFilter.value))
  if (podNamespace.value) list = list.filter((p) => p.namespace === podNamespace.value)
  list = list.filter((p) => matchPodQuickFilter(p, podFilter.value))
  list = filterClusterPods(list, podSearch.value)
  if (restartsOrder.value) {
    const order = restartsOrder.value === 'asc' ? 1 : -1
    list = [...list].sort((a, b) => ((a.restarts ?? 0) - (b.restarts ?? 0)) * order)
  }
  return list
})
const filteredDeployments = computed(() => {
  let list = resources.value.deployments || []
  if (depNamespace.value) list = list.filter((item) => item.namespace === depNamespace.value)
  if (depSearch.value) {
    const keyword = depSearch.value.toLowerCase()
    list = list.filter((item) => item.name.toLowerCase().includes(keyword))
  }
  return list
})
const filteredServices = computed(() => {
  let list = resources.value.services || []
  if (svcNamespace.value) list = list.filter((item) => item.namespace === svcNamespace.value)
  if (svcSearch.value) {
    const keyword = svcSearch.value.toLowerCase()
    list = list.filter((item) => item.name.toLowerCase().includes(keyword))
  }
  return list
})
const filteredEvents = computed(() => {
  let list = clusterEvents.value
  if (eventType.value) list = list.filter((e) => e.type === eventType.value)
  if (eventNs.value) list = list.filter((e) => e.namespace === eventNs.value)
  if (eventSearch.value) {
    const keyword = eventSearch.value.toLowerCase()
    list = list.filter((e) =>
      [e.reason, e.message, e.involved_name, e.involved_kind]
        .some((value) => String(value || '').toLowerCase().includes(keyword)),
    )
  }
  return list
})

const pagedNamespaces = computed(() => {
  const list = resources.value.namespace_overview || []
  const start = (nsPage.value - 1) * nsPageSize.value
  return list.slice(start, start + nsPageSize.value)
})
const pagedNodes = computed(() => {
  const start = (nodePage.value - 1) * nodePageSize.value
  return nodes.value.slice(start, start + nodePageSize.value)
})
const pagedPods = computed(() => {
  const start = (podPage.value - 1) * podPageSize.value
  return filteredPods.value.slice(start, start + podPageSize.value)
})
const pagedDeployments = computed(() => {
  const start = (depPage.value - 1) * depPageSize.value
  return filteredDeployments.value.slice(start, start + depPageSize.value)
})
const pagedServices = computed(() => {
  const start = (svcPage.value - 1) * svcPageSize.value
  return filteredServices.value.slice(start, start + svcPageSize.value)
})
const pagedEvents = computed(() => {
  const start = (evPage.value - 1) * evPageSize.value
  return filteredEvents.value.slice(start, start + evPageSize.value)
})
const pagedPodEvents = computed(() => {
  const start = (eventPage.value - 1) * eventPageSize.value
  return podEvents.value.slice(start, start + eventPageSize.value)
})

watch(podSearch, () => { podPage.value = 1 })
watch(podNamespace, () => { podPage.value = 1 })
watch(podFilter, () => { podPage.value = 1 })
watch(deployFilter, () => { podPage.value = 1 })
watch(depSearch, () => { depPage.value = 1 })
watch(depNamespace, () => { depPage.value = 1 })
watch(svcSearch, () => { svcPage.value = 1 })
watch(svcNamespace, () => { svcPage.value = 1 })
watch([eventType, eventNs, eventSearch], () => { evPage.value = 1 })
watch(drawerTab, (tab) => {
  if (!drawerVisible.value || !selectedPod.value) return
  if (tab === 'logs' && !podLogs.value) loadPodLogs()
  if (tab === 'events' && !podEvents.value.length) loadPodEvents()
})

const lastRefreshText = computed(() => {
  if (!lastRefreshAt.value) return ''
  const diff = Math.max(0, Math.round((nowTick.value - lastRefreshAt.value) / 1000))
  if (diff < 60) return `${diff} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  return `${Math.floor(diff / 3600)} 小时前`
})

function statusType(status: string) {
  return status === 'running' ? 'success' : status === 'stopped' ? 'danger' : 'warning'
}

function podStatusType(status: string) {
  if (status === 'Running' || status === 'Succeeded') return 'success'
  if (['Failed', 'CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'CreateContainerConfigError'].includes(status)) return 'danger'
  if (['Pending', 'NotReady', 'ContainersNotReady'].includes(status)) return 'warning'
  return 'info'
}

function podReasonType(value: string) {
  if (!value) return 'info'
  if (['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'CreateContainerConfigError', 'Failed'].includes(value)) return 'danger'
  if (['Pending', 'NotReady', 'ContainersNotReady', 'ContainerCreating', 'BackOff'].includes(value)) return 'warning'
  return 'info'
}

function depStatusType(status: string) {
  return status === 'running' ? 'success' : status === 'error' ? 'danger' : 'warning'
}

function sideHint(key: string) {
  if (key === 'pods') return '建议先查看日志和事件，再决定是否删除或等待自愈。'
  if (key === 'deployments') return '建议检查副本数和滚动状态，必要时执行重启。'
  return '建议联动节点状态和资源负载继续排查。'
}

function eventDotClass(type?: string) {
  return type === 'Warning' ? 'event-dot-warning' : 'event-dot-normal'
}

function allocLevel(percent: number) {
  if (percent >= 85) return 'danger'
  if (percent >= 70) return 'warn'
  return ''
}

function allocTextClass(percent: number) {
  return percent >= 85 ? 'text-warning' : ''
}

function fmtGi(mi: number) {
  if (!mi) return '0'
  if (mi >= 1024) return `${(mi / 1024).toFixed(1)} Gi`
  return `${Math.round(mi)} Mi`
}

function formatMemory(value: string) {
  if (!value) return '-'
  const num = parseInt(value)
  if (value.endsWith('Ki')) return (num / 1048576).toFixed(1) + ' GB'
  if (value.endsWith('Mi')) return (num / 1024).toFixed(1) + ' GB'
  if (value.endsWith('Gi')) return num.toFixed(1) + ' GB'
  return value
}

function formatTime(value?: string) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return value
  }
}

function openEditDialog() {
  Object.assign(clusterForm, {
    name: cluster.value.name || clusterName.value,
    endpoint: cluster.value.endpoint || '',
    token: '',
    description: cluster.value.description || '',
  })
  editVisible.value = true
}

async function saveCluster() {
  const valid = await clusterFormRef.value?.validate().catch(() => false)
  if (!valid) return

  clusterSaving.value = true
  try {
    const res: any = await updateCluster(clusterName.value, { ...clusterForm })
    const nextName = res.data?.name || clusterForm.name
    cluster.value = res.data || cluster.value
    editVisible.value = false
    ElMessage.success('集群配置已更新')
    if (nextName !== clusterName.value) {
      await router.replace({ name: 'ContainerDetail', params: { name: nextName }, query: route.query })
    } else {
      await loadClusterDetail()
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存集群配置失败')
  } finally {
    clusterSaving.value = false
  }
}

async function testSavedConnection() {
  connectionTesting.value = true
  try {
    const res: any = await testSavedClusterConnection(clusterName.value)
    const result = res.data || {}
    cluster.value.status = result.ok ? 'running' : 'stopped'
    cluster.value.status_message = result.ok ? '' : (result.error || '连接失败')
    if (result.version) cluster.value.version = result.version
    if (result.ok) ElMessage.success(`连接正常${result.version ? ` · ${result.version}` : ''}`)
    else ElMessage.error(result.error || '连接失败')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '连接检测失败')
  } finally {
    connectionTesting.value = false
  }
}

async function downloadKubeconfig() {
  kubeconfigDownloading.value = true
  try {
    const response: any = await downloadClusterKubeconfig(clusterName.value)
    const disposition = response.headers?.['content-disposition'] || ''
    const filenameMatch = disposition.match(/filename="?([^";]+)"?/)
    const filename = filenameMatch?.[1] || `${clusterName.value}-kubeconfig.yaml`
    const blobUrl = URL.createObjectURL(new Blob([response.data], { type: 'application/x-yaml' }))
    const anchor = document.createElement('a')
    anchor.href = blobUrl
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(blobUrl)
    ElMessage.success('kubeconfig 已开始下载')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '下载 kubeconfig 失败')
  } finally {
    kubeconfigDownloading.value = false
  }
}

function resetMaintenanceState() {
  maintenanceNodeName.value = ''
  maintenancePreview.value = null
  maintenanceConfirmNode.value = ''
  maintenancePreviewLoading.value = false
  maintenanceSubmitting.value = false
}

function openMaintenanceDialog(node?: K8sNode) {
  maintenanceVisible.value = true
  maintenancePreview.value = null
  maintenanceConfirmNode.value = ''
  maintenanceNodeName.value = node?.name || nodes.value[0]?.name || ''
  if (maintenanceNodeName.value) loadMaintenancePreview()
}

async function loadMaintenancePreview() {
  const nodeName = maintenanceNodeName.value
  maintenanceConfirmNode.value = ''
  maintenancePreview.value = null
  if (!nodeName) return

  maintenancePreviewLoading.value = true
  try {
    const res: any = await getNodeMaintenancePreview(clusterName.value, nodeName)
    if (maintenanceNodeName.value === nodeName) maintenancePreview.value = res.data || null
  } catch (e: any) {
    if (maintenanceNodeName.value === nodeName) {
      ElMessage.error(e?.response?.data?.detail || '节点维护预检失败')
    }
  } finally {
    if (maintenanceNodeName.value === nodeName) maintenancePreviewLoading.value = false
  }
}

async function updateNodeScheduling(unschedulable: boolean) {
  if (!maintenanceActionReady.value) return
  maintenanceSubmitting.value = true
  try {
    const res: any = await cordonClusterNode(clusterName.value, maintenanceNodeName.value, {
      confirm_node: maintenanceConfirmNode.value.trim(),
      unschedulable,
    })
    ElMessage.success(res.msg || (unschedulable ? 'Cordon 已执行' : '节点已恢复调度'))
    await refreshAll()
    await loadMaintenancePreview()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '节点调度状态更新失败')
  } finally {
    maintenanceSubmitting.value = false
  }
}

function cordonNode() {
  return updateNodeScheduling(true)
}

function restoreNodeScheduling() {
  return updateNodeScheduling(false)
}

async function drainNode() {
  if (!maintenanceActionReady.value || maintenancePreview.value?.blocked.length) return
  maintenanceSubmitting.value = true
  try {
    const res: any = await drainClusterNode(clusterName.value, maintenanceNodeName.value, {
      confirm_node: maintenanceConfirmNode.value.trim(),
      grace_period_seconds: 30,
    })
    const failed = res.data?.failed?.length || 0
    if (failed) ElMessage.warning(`已提交驱逐请求，${failed} 个 Pod 未能驱逐`)
    else ElMessage.success(res.msg || '驱逐请求已提交')
    await refreshAll()
    await loadMaintenancePreview()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '节点 Drain 失败')
  } finally {
    maintenanceSubmitting.value = false
  }
}

function gotoTab(tab: string, filter?: PodQuickFilter) {
  activeTab.value = tab
  if (tab === 'pods' && filter) podFilter.value = filter
}

function setPodFilter(filter: PodQuickFilter) {
  podFilter.value = filter
}

function onAnomalyClick(key: string) {
  if (key === 'pods') gotoTab('pods', 'abnormal')
  else gotoTab(key)
}

function toggleRestartsOrder() {
  restartsOrder.value = restartsOrder.value === 'desc' ? 'asc' : restartsOrder.value === 'asc' ? '' : 'desc'
}

function drilldownDeployment(row: K8sDeployment) {
  deployFilter.value = row.name
  podNamespace.value = ''
  gotoTab('pods', 'all')
}

function clearDeployFilter() {
  deployFilter.value = ''
}

function copyLogs() {
  if (!podLogs.value) return
  navigator.clipboard.writeText(podLogs.value).then(
    () => ElMessage.success('已复制到剪贴板'),
    () => ElMessage.error('复制失败'),
  )
}

function downloadLogs() {
  if (!podLogs.value || !selectedPod.value) return
  const blob = new Blob([podLogs.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${selectedPod.value.namespace}_${selectedPod.value.name}.log`
  anchor.click()
  URL.revokeObjectURL(url)
}

function openServiceDetail(row: K8sService) {
  selectedService.value = row
  svcDetailVisible.value = true
}

function openNodeDetail(row: K8sNode) {
  selectedNode.value = row
  nodeDetailVisible.value = true
}

function openNamespaceDetail(row: K8sNamespace) {
  selectedNamespace.value = row
  nsDetailVisible.value = true
}

function openPodDrawer(row: K8sPod, tab: 'logs' | 'events') {
  selectedPod.value = row
  podLogs.value = ''
  podEvents.value = []
  eventPage.value = 1
  drawerTab.value = tab
  drawerVisible.value = true
  if (tab === 'logs') loadPodLogs()
  else loadPodEvents()
}

async function loadPodLogs() {
  if (!selectedPod.value) return
  logsLoading.value = true
  try {
    const res: any = await getPodLogs(clusterName.value, selectedPod.value.namespace, selectedPod.value.name, { tail_lines: 300 })
    podLogs.value = res.data?.logs || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载日志失败')
  } finally {
    logsLoading.value = false
  }
}

async function loadPodEvents() {
  if (!selectedPod.value) return
  eventsLoading.value = true
  try {
    const res: any = await getPodEvents(clusterName.value, selectedPod.value.namespace, selectedPod.value.name)
    podEvents.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载事件失败')
  } finally {
    eventsLoading.value = false
  }
}

async function confirmDeletePod(row: K8sPod) {
  try {
    await ElMessageBox.confirm(
      `确定删除 Pod ${row.namespace}/${row.name}？删除后如该 Pod 属于某个工作负载，系统将自动创建新 Pod 替代。`,
      '删除 Pod',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteClusterPod(clusterName.value, row.namespace, row.name)
    ElMessage.success('Pod 已删除')
    await refreshAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function confirmRestartDeployment(row: K8sDeployment) {
  try {
    await ElMessageBox.confirm(
      `确定滚动重启 Deployment ${row.namespace}/${row.name}？`,
      '重启 Deployment',
      { type: 'warning', confirmButtonText: '重启', cancelButtonText: '取消' },
    )
    await restartClusterDeployment(clusterName.value, row.namespace, row.name)
    ElMessage.success('重启已触发')
    await refreshAll()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function confirmDeleteCluster() {
  try {
    await ElMessageBox.confirm(
      `确定删除集群「${clusterName.value}」？删除后需重新接入才能查看资源。`,
      '删除集群',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteCluster(clusterName.value)
    ElMessage.success('删除成功')
    router.push('/assets/containers')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function fetchCluster() {
  clusterError.value = ''
  if (!clusterName.value) return false
  try {
    const res: any = await getCluster(clusterName.value)
    cluster.value = res.data
    return true
  } catch (e: any) {
    clusterError.value = e?.response?.data?.detail || '加载失败'
    return false
  }
}

async function fetchResources() {
  if (!clusterName.value) return
  refreshing.value = true
  resourcesError.value = ''
  try {
    const res: any = await getClusterResources(clusterName.value)
    resources.value = res.data
    lastRefreshAt.value = Date.now()
    nowTick.value = Date.now()
    cluster.value.status = res.data.connected ? 'running' : 'stopped'
    cluster.value.status_message = res.data.connected ? '' : (res.data.error || '连接失败')
    cluster.value.version = res.data.version || cluster.value.version
    cluster.value.node_count = res.data.node_count ?? cluster.value.node_count
  } catch (e: any) {
    resourcesError.value = e?.response?.data?.detail || '加载失败'
  } finally {
    refreshing.value = false
    initialLoading.value = false
  }
}

async function fetchClusterEvents() {
  if (!clusterName.value) return
  clusterEventsLoading.value = true
  try {
    const res: any = await getClusterEvents(clusterName.value)
    clusterEvents.value = res.data || []
  } catch {
    clusterEvents.value = []
  } finally {
    clusterEventsLoading.value = false
  }
}

async function refreshAll() {
  await Promise.all([fetchResources(), fetchClusterEvents()])
}

async function loadClusterDetail() {
  const routeRef = clusterName.value
  if (!routeRef || activeLoadRef === routeRef) return
  activeLoadRef = routeRef
  if (cluster.value.name && cluster.value.name !== routeRef) {
    cluster.value = {}
    resources.value = {}
    clusterEvents.value = []
  }
  initialLoading.value = true
  try {
    if (await fetchCluster()) await refreshAll()
    else initialLoading.value = false
  } finally {
    if (activeLoadRef === routeRef) activeLoadRef = ''
  }
}

let activeLoadRef = ''
watch(clusterName, loadClusterDetail)

let timer: ReturnType<typeof setInterval> | null = null
let ticker: ReturnType<typeof setInterval> | null = null

function setupTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (autoRefresh.value) timer = setInterval(refreshAll, 30000)
}

watch(autoRefresh, setupTimer)

onActivated(() => {
  loadClusterDetail()
  setupTimer()
  ticker = setInterval(() => { nowTick.value = Date.now() }, 5000)
})

onDeactivated(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (ticker) {
    clearInterval(ticker)
    ticker = null
  }
})
</script>

<style scoped>
.cluster-detail {
  min-width: 0;
}

.surface-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.detail-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.detail-header-copy {
  min-width: 0;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-title {
  margin: 0;
}

.detail-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.refresh-relative {
  color: var(--success-color);
  font-style: normal;
}

.detail-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.auto-refresh-control {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-right: 2px;
}

.auto-refresh-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.auto-refresh-switch {
  flex: none;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.tag-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 5px;
  border-radius: 50%;
}

.dot-success {
  background: var(--success-color);
}

.dot-danger {
  background: var(--danger-color);
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 16px;
  background: color-mix(in srgb, var(--danger-color) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--danger-color) 25%, transparent);
  border-radius: var(--border-radius);
}

.error-banner-text {
  color: var(--danger-color);
  font-size: 13px;
}

.warning-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
  background: color-mix(in srgb, var(--warning-color) 10%, var(--surface-color));
  border: 1px solid color-mix(in srgb, var(--warning-color) 24%, var(--surface-color));
  border-radius: var(--border-radius);
  color: color-mix(in srgb, var(--warning-color) 50%, var(--text-primary));
  font-size: 13px;
  font-weight: 600;
}

.warning-meta {
  color: var(--text-secondary);
  font-weight: 500;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  min-width: 0;
  padding: 14px 16px;
}

button.summary-card {
  display: block;
  width: 100%;
  text-align: left;
  color: inherit;
  font: inherit;
}

.summary-card.clickable {
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.summary-card.clickable:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px color-mix(in srgb, var(--primary-color) 8%, transparent);
}

.summary-card.clickable:focus-visible,
.tab-button:focus-visible,
.chip:focus-visible,
.sort-header:focus-visible,
.side-item.clickable:focus-visible,
.rc-node:focus-visible,
.quick-action:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.summary-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.go-link {
  color: var(--primary-color);
  font-weight: 600;
}

.summary-value {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 750;
}

.summary-value .sub {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.summary-foot {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

.progress {
  height: 6px;
  margin-top: 10px;
  overflow: hidden;
  background: color-mix(in srgb, var(--border-color) 65%, var(--surface-color));
  border-radius: 999px;
}

.progress > i {
  display: block;
  height: 100%;
  background: var(--primary-color);
  border-radius: 999px;
}

.progress.warn > i {
  background: var(--warning-color);
}

.progress.danger > i {
  background: var(--danger-color);
}

.progress-note {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 11.5px;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.92fr);
  gap: 16px;
}

.workbench-main {
  overflow: hidden;
}

.tabs-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.tab-button {
  height: 42px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  border-bottom: 2px solid transparent;
  cursor: pointer;
}

.tab-button.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.tab-badge {
  display: inline-block;
  min-width: 17px;
  padding: 0 5px;
  margin-left: 5px;
  font-size: 11px;
  line-height: 16px;
  text-align: center;
  border-radius: 999px;
  font-weight: 700;
}

.tab-badge.danger {
  background: color-mix(in srgb, var(--danger-color) 12%, transparent);
  color: color-mix(in srgb, var(--danger-color) 55%, var(--text-primary));
}

.tab-badge.warning {
  background: color-mix(in srgb, var(--warning-color) 15%, transparent);
  color: color-mix(in srgb, var(--warning-color) 50%, var(--text-primary));
}

.section-body {
  padding: 14px 18px 16px;
}

.tool-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tool-select {
  width: 160px;
}

.tool-select-sm {
  width: 120px;
}

.tool-search {
  width: 260px;
}

.tool-count {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 13px;
}

.chip-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.chip {
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  border-radius: 999px;
  padding: 3px 12px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-secondary);
}

.chip:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.chip.active {
  background: var(--primary-bg);
  border-color: var(--primary-color);
  color: var(--primary-color);
  font-weight: 600;
}

.chip.danger.active {
  background: color-mix(in srgb, var(--danger-color) 10%, transparent);
  border-color: var(--danger-color);
  color: color-mix(in srgb, var(--danger-color) 55%, var(--text-primary));
}

.filter-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 7px 12px;
  border-radius: 6px;
  background: var(--primary-bg);
  border: 1px solid color-mix(in srgb, var(--primary-color) 25%, transparent);
  font-size: 12.5px;
  color: var(--primary-color);
}

.filter-banner > span,
.filter-banner :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pane-tip {
  margin-bottom: 12px;
}

.sort-header {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: inherit;
  font-weight: inherit;
  cursor: pointer;
  padding: 0;
}

.sort-header:hover {
  color: var(--primary-color);
}

.sort-idle {
  opacity: 0.45;
}

.restarts-strong {
  font-weight: 700;
}

.alloc-cell {
  min-width: 120px;
}

.alloc-cell .progress {
  margin-top: 0;
}

.node-status-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-wrap: wrap;
}

.resource-primary {
  display: grid;
  gap: 4px;
}

.resource-primary strong {
  color: var(--text-primary);
}

.resource-primary span {
  color: var(--text-muted);
  font-size: 12px;
}

.clickable-rows :deep(.el-table__row) {
  cursor: pointer;
}

.event-list {
  display: grid;
}

.event-item {
  display: flex;
  gap: 12px;
  padding: 10px 4px;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 68%, var(--surface-color));
}

.event-item:last-child {
  border-bottom: none;
}

.event-dot {
  flex: none;
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
}

.event-dot-normal {
  background: var(--primary-color);
}

.event-dot-warning {
  background: var(--warning-color);
}

.event-body {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 3px;
}

.event-body strong {
  font-size: 13px;
}

.event-body p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12.5px;
  word-break: break-all;
}

.event-sub {
  color: var(--text-muted);
  font-size: 12px;
}

.event-time {
  flex: none;
  color: var(--text-muted);
  font-size: 12px;
}

.workbench-side {
  display: grid;
  gap: 16px;
  align-content: start;
}

.side-card {
  padding: 16px;
}

.side-card-head {
  display: grid;
  gap: 3px;
  margin-bottom: 12px;
}

.side-card-head h3 {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.side-card-subtitle {
  color: var(--text-secondary);
  font-size: 12px;
}

.side-list {
  display: grid;
  gap: 10px;
}

.side-item {
  width: 100%;
  display: grid;
  gap: 6px;
  padding: 12px;
  text-align: left;
  color: var(--text-primary);
  font: inherit;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--surface-color);
}

.side-item.clickable {
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.side-item.clickable:hover {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.side-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.side-item span {
  color: var(--text-secondary);
  font-size: 12px;
}

.rc-chain {
  display: grid;
}

.rc-node {
  width: 100%;
  position: relative;
  display: grid;
  gap: 3px;
  padding: 10px 10px 10px 26px;
  color: var(--text-primary);
  text-align: left;
  font: inherit;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

.rc-node + .rc-node {
  margin-top: 8px;
}

.rc-node + .rc-node::before {
  content: '';
  position: absolute;
  left: 12px;
  top: -8px;
  width: 1px;
  height: 8px;
  background: var(--border-color);
}

.rc-node::after {
  content: '';
  position: absolute;
  left: 8px;
  top: 15px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.rc-node.root {
  background: color-mix(in srgb, var(--danger-color) 7%, transparent);
}

.rc-node.root::after {
  background: var(--danger-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--danger-color) 18%, transparent);
}

.rc-node.mid {
  background: color-mix(in srgb, var(--warning-color) 8%, transparent);
}

.rc-node.mid::after {
  background: var(--warning-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--warning-color) 16%, transparent);
}

.rc-node strong {
  font-size: 12.5px;
}

.rc-node > span:not(.rc-tag) {
  color: var(--text-muted);
  font-size: 11.5px;
}

.rc-tag {
  position: absolute;
  right: 8px;
  top: 8px;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
}

.rc-node.root .rc-tag {
  background: color-mix(in srgb, var(--danger-color) 14%, transparent);
  color: color-mix(in srgb, var(--danger-color) 55%, var(--text-primary));
}

.rc-node.mid .rc-tag {
  background: color-mix(in srgb, var(--warning-color) 16%, transparent);
  color: color-mix(in srgb, var(--warning-color) 50%, var(--text-primary));
}

.ns-heat-list {
  display: grid;
}

.ns-bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 42px;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  font-size: 12.5px;
}

.ns-bar-row .progress {
  margin-top: 0;
}

.ns-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-actions-list {
  display: grid;
  gap: 2px;
}

.quick-action {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  width: 100%;
  padding: 9px 0;
  color: var(--text-primary);
  text-align: left;
  font: inherit;
  background: transparent;
  border: 0;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 72%, transparent);
  cursor: pointer;
}

.quick-action:last-child {
  border-bottom: 0;
}

.quick-action > .el-icon {
  margin-top: 2px;
  color: var(--primary-color);
}

.quick-action span {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.quick-action strong {
  font-size: 13px;
}

.quick-action small {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.quick-action:hover:not(:disabled) strong {
  color: var(--primary-color);
}

.quick-action:disabled {
  color: var(--text-muted);
  cursor: not-allowed;
}

.quick-action-warning > .el-icon,
.quick-action-warning:hover:not(:disabled) strong {
  color: var(--warning-color);
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

.drawer-tabs {
  padding: 0 18px;
}

.drawer-body {
  padding: 14px 18px;
}

.dialog-notice {
  margin-bottom: 16px;
}

.cluster-edit-form {
  display: grid;
  gap: 2px;
}

.maintenance-dialog {
  display: grid;
  gap: 2px;
}

.maintenance-node-select {
  width: 100%;
}

.node-option-meta {
  float: right;
  color: var(--text-muted);
  font-size: 12px;
}

.maintenance-preview {
  display: grid;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}

.maintenance-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.maintenance-summary b {
  color: var(--text-primary);
}

.maintenance-list-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.maintenance-list-section {
  min-width: 0;
}

.maintenance-list-section h4 {
  margin: 0 0 6px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.maintenance-list-section p {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin: 0;
  padding: 5px 0;
  color: var(--text-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 68%, transparent);
}

.maintenance-list-section small {
  color: var(--text-muted);
  font-family: inherit;
  font-size: 11px;
  text-align: right;
}

.maintenance-list-section.is-blocked h4,
.maintenance-list-section.is-blocked small {
  color: var(--danger-color);
}

.maintenance-confirm-form {
  margin-top: 16px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.text-danger {
  color: var(--danger-color);
}

.text-warning {
  color: var(--warning-color);
}

.log-box {
  min-height: 320px;
  max-height: 560px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: var(--surface-color);
  background: var(--text-primary);
  border-radius: 8px;
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

@media (max-width: 1200px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .detail-header,
  .warning-banner {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .detail-header,
  .warning-banner,
  .tool-row {
    flex-direction: column;
  }

  .detail-header-actions,
  .tool-select,
  .tool-search,
  .tool-count {
    width: 100%;
  }

  .detail-header-actions {
    justify-content: flex-start;
  }

  .auto-refresh-control {
    justify-content: space-between;
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .tool-count {
    margin-left: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .summary-card.clickable,
  .side-item.clickable {
    transition: none;
  }
}
</style>
