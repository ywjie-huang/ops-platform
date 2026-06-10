<template>
  <main class="app-detail-page">
    <!-- 面包屑导航 -->
    <nav aria-label="面包屑导航">
      <el-breadcrumb separator="/" class="page-breadcrumb">
        <el-breadcrumb-item :to="{ path: '/deploy/apps' }">应用管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ app.name || appName }}</el-breadcrumb-item>
      </el-breadcrumb>
    </nav>

    <div class="page-header">
      <h2 class="page-title">{{ app.name || '应用详情' }}</h2>
      <div class="header-actions">
        <el-button @click="$router.push(`/deploy/apps/${appName}/edit`)">编辑</el-button>
        <el-popconfirm title="确认删除此应用？删除后不可恢复。" confirm-button-text="删除" confirm-button-type="danger" @confirm="handleDelete">
          <template #reference>
            <el-button type="danger" aria-label="删除此应用">删除</el-button>
          </template>
        </el-popconfirm>
        <el-button @click="$router.push('/deploy/apps')">返回列表</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="detail-tabs" @tab-change="handleTabChange">
      <!-- Tab 1: 概览 -->
      <el-tab-pane label="概览" name="overview">
        <!-- KPI 摘要卡片 -->
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-label">应用状态</div>
            <div class="kpi-value">
              <el-tag :type="app.status === 'active' ? 'success' : 'info'" size="small">
                {{ app.status === 'active' ? '活跃' : '已归档' }}
              </el-tag>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">部署策略</div>
            <div class="kpi-value">
              <el-tag :type="strategyType(app.deploy_strategy)" size="small">{{ strategyLabel(app.deploy_strategy) }}</el-tag>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">环境数</div>
            <div class="kpi-value kpi-number">{{ appEnvs.length }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">最近部署</div>
            <div class="kpi-value kpi-text">{{ lastDeployLabel }}</div>
          </div>
        </div>

        <div class="data-card">
          <el-descriptions :column="2">
            <el-descriptions-item label="应用名称">{{ app.name }}</el-descriptions-item>
            <el-descriptions-item label="应用类型">{{ typeLabel(app.app_type) }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ app.description || '—' }}</el-descriptions-item>
            <el-descriptions-item label="Git 仓库">{{ app.git_url || '—' }}</el-descriptions-item>
            <el-descriptions-item label="默认分支">{{ app.git_branch || '—' }}</el-descriptions-item>
            <el-descriptions-item label="构建模式">{{ buildModeLabel(app.build_mode) }}</el-descriptions-item>
            <el-descriptions-item label="构建命令/Job">{{ buildModeDetail(app) }}</el-descriptions-item>
            <el-descriptions-item label="健康检查">按环境配置</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ app.creator_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(app.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 环境管理 -->
      <el-tab-pane label="环境管理" name="envs">
        <div v-loading="envLoading">
          <div class="env-toolbar">
            <el-button type="primary" size="small" @click="openAddEnvDialog">+ 添加环境</el-button>
          </div>

          <!-- 空状态插图 -->
          <div v-if="!envLoading && appEnvs.length === 0" class="empty-state">
            <svg viewBox="0 0 120 80" fill="none" class="empty-illustration" aria-hidden="true">
              <rect x="20" y="20" width="80" height="44" rx="6" stroke="var(--border-color)" stroke-width="1.5" />
              <rect x="28" y="30" width="28" height="8" rx="3" fill="var(--bg-color)" />
              <rect x="28" y="42" width="52" height="6" rx="3" fill="var(--bg-color)" />
              <circle cx="84" cy="34" r="6" stroke="var(--primary-color)" stroke-width="1.5" stroke-dasharray="3 2" />
              <line x1="56" y1="68" x2="64" y2="68" stroke="var(--border-color)" stroke-width="1.5" stroke-linecap="round" />
            </svg>
            <p class="empty-text">暂无环境配置</p>
            <el-button type="primary" size="small" @click="openAddEnvDialog">+ 添加环境</el-button>
          </div>

          <div v-for="ae in appEnvs" :key="ae.id" class="env-card">
            <div class="env-card-header" @click="toggleEnvCard(ae.env_id)">
              <div class="env-card-title">
                <el-icon class="env-collapse-icon" :class="{ collapsed: collapsedEnvs.has(ae.env_id) }"><ArrowRight /></el-icon>
                <span class="env-name">{{ ae.env_name }}</span>
                <el-tag v-if="ae.approval_required" type="warning" size="small">需审批</el-tag>
                <el-tag :type="ae.enabled ? 'success' : 'info'" size="small">
                  {{ ae.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </div>
              <div class="env-card-actions" @click.stop>
                <el-button size="small" type="primary" @click="openDeployDialog(ae)" :disabled="!ae.enabled">
                  <el-icon><Promotion /></el-icon>部署
                </el-button>
                <el-button size="small" text type="primary" @click="openEnvDialog(ae)">配置</el-button>
                <el-popconfirm title="确认移除此环境配置？" @confirm="handleRemoveEnv(ae.env_id)">
                  <template #reference><el-button size="small" text type="danger" aria-label="移除环境">移除</el-button></template>
                </el-popconfirm>
              </div>
            </div>

            <div class="env-card-body" :class="{ collapsed: collapsedEnvs.has(ae.env_id) }">
              <!-- SSH 策略 -->
              <template v-if="app.deploy_strategy === 'ssh'">
                <div class="env-field"><span class="env-field-label">目标主机：</span>{{ ae.ssh_asset_name ? `${ae.ssh_asset_name} (${ae.ssh_asset_ip})` : '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">部署路径：</span>{{ ae.deploy_path || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">部署脚本：</span><code>{{ ae.deploy_script || '无' }}</code></div>
                <div class="env-field"><span class="env-field-label">健康检查：</span>
                  <template v-if="ae.health_check_port">端口 {{ ae.health_check_port }}（{{ ae.health_check_timeout }}s）</template>
                  <template v-else-if="ae.health_check_url">{{ ae.health_check_url }}</template>
                  <span v-else>未配置</span>
                </div>
              </template>

              <!-- Docker 策略 -->
              <template v-if="app.deploy_strategy === 'docker'">
                <div class="env-field"><span class="env-field-label">Docker 主机：</span>{{ ae.docker_host_name || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">镜像：</span>{{ ae.docker_image || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">容器名：</span>{{ ae.docker_container_name || '—' }}</div>
                <div class="env-field"><span class="env-field-label">端口映射：</span>{{ ae.docker_ports || '—' }}</div>
                <div class="env-field"><span class="env-field-label">网络：</span>{{ ae.docker_network || '—' }}</div>
              </template>

              <!-- K8s 策略 -->
              <template v-if="app.deploy_strategy === 'k8s'">
                <div class="env-field"><span class="env-field-label">K8s 集群：</span>{{ ae.k8s_cluster_name || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">命名空间：</span>{{ ae.k8s_namespace }}</div>
                <div class="env-field"><span class="env-field-label">Deployment：</span>{{ ae.k8s_deployment || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">容器名：</span>{{ ae.k8s_container_name || '—' }}</div>
              </template>

              <!-- 构建产物（每个环境独立） -->
              <template v-if="app.build_mode !== 'jenkins'">
                <div class="env-artifact-divider"></div>
                <div class="env-artifact">
                  <div class="env-artifact-title">构建产物</div>
                  <div v-if="ae.artifact_filename" class="env-artifact-file">
                    <div class="env-artifact-info">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" class="env-artifact-icon" aria-hidden="true">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span class="env-artifact-name">{{ ae.artifact_filename }}</span>
                      <span class="env-artifact-meta">{{ formatSize(ae.artifact_size) }} · {{ formatTime(ae.artifact_uploaded_at) }}</span>
                    </div>
                    <div class="env-artifact-actions">
                      <el-button size="small" type="primary" text @click="handleDownloadArtifact(ae)" aria-label="下载构建产物">
                        <el-icon><Download /></el-icon>下载
                      </el-button>
                      <el-upload
                        :show-file-list="false"
                        :before-upload="(file: File) => handleUploadArtifact(ae.env_id, file)"
                        accept=".jar,.war,.zip,.tar,.tar.gz,.tgz,.gz,.rpm,.deb,.whl,.pyz"
                        :disabled="uploadingEnvId === ae.env_id"
                      >
                        <el-button size="small" text type="primary" :loading="uploadingEnvId === ae.env_id" aria-label="重新上传构建产物">重新上传</el-button>
                      </el-upload>
                      <el-popconfirm title="确认删除此环境的构建产物？" @confirm="handleDeleteArtifact(ae.env_id)">
                        <template #reference><el-button size="small" text type="danger" aria-label="删除构建产物">删除</el-button></template>
                      </el-popconfirm>
                    </div>
                  </div>
                  <div v-else class="env-artifact-empty">
                    <el-upload
                      :show-file-list="false"
                      :before-upload="(file: File) => handleUploadArtifact(ae.env_id, file)"
                      accept=".jar,.war,.zip,.tar,.tar.gz,.tgz,.gz,.rpm,.deb,.whl,.pyz"
                      :disabled="uploadingEnvId === ae.env_id"
                    >
                      <el-button size="small" type="primary" :loading="uploadingEnvId === ae.env_id" aria-label="上传构建产物">
                        <el-icon><UploadFilled /></el-icon>上传构建产物
                      </el-button>
                    </el-upload>
                    <span class="env-artifact-hint">部署前需先上传此环境的构建产物</span>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 构建历史 -->
      <el-tab-pane label="构建历史" name="builds">
        <div class="data-card">
          <div class="build-toolbar">
            <div class="build-filters">
              <el-select v-model="buildFilterStatus" placeholder="状态" clearable size="small" style="width: 100px">
                <el-option label="成功" value="success" />
                <el-option label="失败" value="failed" />
              </el-select>
              <el-input v-model="buildSearch" placeholder="搜索 build_number / commit / tag" clearable size="small" style="width: 240px" />
            </div>
            <div class="build-actions">
              <el-button v-if="app.build_mode === 'webhook'" type="primary" size="small" @click="showWebhookConfig = true">
                Webhook 配置
              </el-button>
              <el-button size="small" @click="openCompareDialog">比较版本</el-button>
              <el-button size="small" @click="showCleanupConfig = true">清理策略</el-button>
              <el-popconfirm title="确认手动清理旧构建？将根据清理策略删除多余记录。" @confirm="handleCleanupBuilds">
                <template #reference><el-button size="small" type="warning">手动清理</el-button></template>
              </el-popconfirm>
            </div>
          </div>
          <el-table :data="builds" stripe v-loading="buildsLoading">
            <el-table-column prop="build_number" label="Build #" width="140">
              <template #default="{ row }"><code class="build-number">{{ row.build_number }}</code></template>
            </el-table-column>
            <el-table-column prop="tag" label="标签" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.tag" size="small" type="warning">{{ row.tag }}</el-tag>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="commit" label="Commit" width="100">
              <template #default="{ row }"><code v-if="row.commit" class="commit-text">{{ row.commit.substring(0, 7) }}</code><span v-else>—</span></template>
            </el-table-column>
            <el-table-column prop="branch" label="分支" width="100" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }"><el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status === 'success' ? '成功' : '失败' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="artifact_size" label="大小" width="90">
              <template #default="{ row }">{{ formatSize(row.artifact_size) }}</template>
            </el-table-column>
            <el-table-column prop="deploy_count" label="部署次数" width="90" />
            <el-table-column prop="created_at" label="创建时间" min-width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" text @click="openDeployBuildDialog(row)" :disabled="row.status !== 'success'">部署</el-button>
                <el-button size="small" :type="row.is_pinned ? 'warning' : 'default'" text @click="togglePin(row)">
                  {{ row.is_pinned ? '取消固定' : '固定' }}
                </el-button>
                <el-popconfirm title="确认删除此构建记录？" @confirm="handleDeleteBuild(row.build_number)">
                  <template #reference><el-button size="small" text type="danger">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="buildsTotal > buildsPageSize" class="table-pagination">
            <el-pagination
              v-model:current-page="buildsPage"
              :page-size="buildsPageSize"
              :total="buildsTotal"
              layout="total, prev, pager, next"
              @current-change="fetchBuilds"
            />
          </div>
          <el-empty v-if="!buildsLoading && builds.length === 0" description="暂无构建记录" />
        </div>
      </el-tab-pane>

      <!-- Tab 4: 部署历史 -->
      <el-tab-pane label="部署历史" name="history">
        <div class="data-card">
          <el-table :data="records" stripe v-loading="recordsLoading" @row-click="(row: any) => $router.push(`/deploy/records/${row.id}`)" row-class-name="clickable-row">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="env_name" label="环境" width="100">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.env_name || '—' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="130">
              <template #default="{ row }"><code class="version-text">{{ row.version || '—' }}</code></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }"><el-tag :type="statusTypeMap[row.status]" size="small">{{ statusLabelMap[row.status] || row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="trigger_user_name" label="触发人" width="90" />
            <el-table-column prop="duration" label="耗时" width="90">
              <template #default="{ row }">
                <span :aria-label="row.duration != null ? `${Math.round(row.duration)}秒` : ''">{{ row.duration != null ? formatDuration(row.duration) : '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" min-width="170">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <div v-if="recordsTotal > recordsPageSize" class="table-pagination">
            <el-pagination
              v-model:current-page="recordsPage"
              :page-size="recordsPageSize"
              :total="recordsTotal"
              layout="total, prev, pager, next"
              @current-change="fetchRecords"
            />
          </div>
          <el-empty v-if="!recordsLoading && records.length === 0" description="暂无部署记录">
            <template #image>
              <svg viewBox="0 0 120 80" fill="none" class="empty-illustration-sm" aria-hidden="true">
                <rect x="25" y="18" width="70" height="48" rx="6" stroke="var(--border-color)" stroke-width="1.5" />
                <line x1="35" y1="32" x2="85" y2="32" stroke="var(--bg-color)" stroke-width="2" />
                <line x1="35" y1="42" x2="70" y2="42" stroke="var(--bg-color)" stroke-width="2" />
                <line x1="35" y1="52" x2="55" y2="52" stroke="var(--bg-color)" stroke-width="2" />
              </svg>
            </template>
          </el-empty>
        </div>
      </el-tab-pane>

      <!-- Tab 4: 配置管理 -->
      <el-tab-pane label="配置管理" name="configs">
        <div class="data-card">
          <div class="config-toolbar">
            <el-input v-model="configSearch" placeholder="搜索 Key 或说明..." clearable size="small" class="config-search" prefix-icon="Search" />
            <el-button type="primary" size="small" @click="openConfigDialog()">+ 新增配置</el-button>
          </div>
          <el-table :data="filteredConfigs" stripe v-loading="configsLoading">
            <el-table-column prop="key" label="Key" min-width="160">
              <template #default="{ row }"><code class="config-key">{{ row.key }}</code></template>
            </el-table-column>
            <el-table-column prop="value" label="Value" min-width="200">
              <template #default="{ row }">
                <span v-if="row.is_encrypted" class="config-encrypted">
                  <el-icon class="config-encrypted-icon"><Lock /></el-icon>******
                </span>
                <span v-else class="config-value">{{ row.value || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="env_name" label="环境" width="100">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.env_name || '全局' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="is_encrypted" label="加密" width="70">
              <template #default="{ row }">
                <el-icon v-if="row.is_encrypted" class="config-encrypted-icon"><Lock /></el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="140" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="openConfigDialog(row)">编辑</el-button>
                <el-popconfirm title="确认删除此配置项？" @confirm="handleDeleteConfig(row.id)">
                  <template #reference><el-button size="small" text type="danger" aria-label="删除配置项">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!configsLoading && filteredConfigs.length === 0" :description="configSearch ? '无匹配配置项' : '暂无配置项'">
            <template #image>
              <svg viewBox="0 0 120 80" fill="none" class="empty-illustration-sm" aria-hidden="true">
                <circle cx="60" cy="38" r="18" stroke="var(--border-color)" stroke-width="1.5" />
                <path d="M72 50 L82 60" stroke="var(--border-color)" stroke-width="2" stroke-linecap="round" />
                <circle cx="60" cy="38" r="8" stroke="var(--primary-color)" stroke-width="1.5" stroke-dasharray="3 2" />
              </svg>
            </template>
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加环境弹窗 -->
    <el-dialog v-model="addEnvDialogVisible" title="添加环境" width="420px" top="5vh" aria-labelledby="add-env-title">
      <el-form label-width="80px">
        <el-form-item label="选择环境">
          <el-select v-model="addEnvId" placeholder="请选择环境" class="dialog-select-full">
            <el-option
              v-for="e in availableEnvs"
              :key="e.id"
              :label="e.display_name || e.name"
              :value="e.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addEnvDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddEnv" :loading="addEnvLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 环境配置弹窗 -->
    <el-dialog v-model="envDialogVisible" :title="`配置 — ${editingEnv?.env_name || ''}`" width="680px" top="5vh" aria-labelledby="env-dialog-title">
      <el-form v-if="editingEnv" :model="envForm" label-width="110px">
        <el-form-item label="启用">
          <el-switch v-model="envForm.enabled" />
        </el-form-item>

        <!-- SSH 配置 -->
        <template v-if="app.deploy_strategy === 'ssh'">
          <el-form-item label="目标主机">
            <el-select v-model="envForm.ssh_asset_id" placeholder="选择主机" class="dialog-select-full" filterable clearable>
              <el-option v-for="a in assets" :key="a.id" :label="`${a.name} (${a.ip_address})`" :value="a.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部署路径">
            <el-input v-model="envForm.deploy_path" placeholder="/opt/apps/myapp/" />
          </el-form-item>
          <el-form-item label="部署脚本">
            <el-input v-model="envForm.deploy_script" type="textarea" :rows="5" placeholder="# 部署后执行的脚本&#10;cd /opt/apps/myapp&#10;./restart.sh" />
          </el-form-item>
          <el-form-item label="健康检查端口">
            <el-input-number v-model="envForm.health_check_port" :min="0" :max="65535" placeholder="如：8080" class="input-number-200" />
            <span class="form-hint">部署后检测目标端口是否可达，0 表示不检测</span>
          </el-form-item>
          <el-form-item label="健康检查 URL">
            <el-input v-model="envForm.health_check_url" placeholder="http://host:port/health（可选回退）" />
          </el-form-item>
          <el-form-item label="超时时间（秒）">
            <el-input-number v-model="envForm.health_check_timeout" :min="5" :max="300" :step="5" />
          </el-form-item>
        </template>

        <!-- Docker 配置 -->
        <template v-if="app.deploy_strategy === 'docker'">
          <el-form-item label="Docker 主机">
            <el-select v-model="envForm.docker_host_id" placeholder="选择 Docker 主机" class="dialog-select-full" filterable clearable>
              <el-option v-for="h in dockerHosts" :key="h.id" :label="h.name" :value="h.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="镜像">
            <el-input v-model="envForm.docker_image" placeholder="registry.example.com/app:latest" />
          </el-form-item>
          <el-form-item label="容器名">
            <el-input v-model="envForm.docker_container_name" placeholder="my-app" />
          </el-form-item>
          <el-form-item label="端口映射">
            <el-input v-model="envForm.docker_ports" placeholder="8080:80,443:443" />
          </el-form-item>
          <el-form-item label="环境变量">
            <el-input v-model="envForm.docker_env_vars" type="textarea" :rows="3" placeholder='{"KEY":"value","DB_HOST":"10.0.0.1"}' />
          </el-form-item>
          <el-form-item label="网络">
            <el-input v-model="envForm.docker_network" placeholder="bridge / host / 自定义网络名" />
          </el-form-item>
          <el-form-item label="额外参数">
            <el-input v-model="envForm.docker_extra_args" type="textarea" :rows="2" placeholder="--restart=always -v /data:/data" />
          </el-form-item>
        </template>

        <!-- K8s 配置 -->
        <template v-if="app.deploy_strategy === 'k8s'">
          <el-form-item label="K8s 集群">
            <el-select v-model="envForm.k8s_cluster_id" placeholder="选择集群" class="dialog-select-full" filterable clearable>
              <el-option v-for="c in k8sClusters" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="命名空间">
            <el-input v-model="envForm.k8s_namespace" placeholder="default" />
          </el-form-item>
          <el-form-item label="Deployment">
            <el-input v-model="envForm.k8s_deployment" placeholder="my-deployment" />
          </el-form-item>
          <el-form-item label="容器名">
            <el-input v-model="envForm.k8s_container_name" placeholder="my-container" />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEnv" :loading="envSaving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 部署确认弹窗 -->
    <el-dialog v-model="deployDialogVisible" title="确认部署" width="460px" top="5vh" aria-labelledby="deploy-dialog-title">
      <div v-if="deployingEnv" class="deploy-confirm">
        <p>应用：<strong>{{ app.name }}</strong></p>
        <p>环境：<strong>{{ deployingEnv.env_name }}</strong></p>
        <p v-if="deployingEnv.approval_required" class="deploy-warn">
          <el-icon><Warning /></el-icon>该环境需要审批，部署将进入待审批状态
        </p>
        <div class="deploy-env-summary">
          <template v-if="app.deploy_strategy === 'ssh'">
            <span>目标主机：{{ deployingEnv.ssh_asset_name || '未配置' }}</span>
            <span>路径：{{ deployingEnv.deploy_path || '未配置' }}</span>
          </template>
          <template v-if="app.deploy_strategy === 'docker'">
            <span>Docker 主机：{{ deployingEnv.docker_host_name || '未配置' }}</span>
            <span>镜像：{{ deployingEnv.docker_image || '未配置' }}</span>
          </template>
          <template v-if="app.deploy_strategy === 'k8s'">
            <span>集群：{{ deployingEnv.k8s_cluster_name || '未配置' }}</span>
            <span>Deployment：{{ deployingEnv.k8s_deployment || '未配置' }}</span>
          </template>
        </div>
        <p v-if="!isDeployReady(deployingEnv)" class="deploy-warn">
          <el-icon><Warning /></el-icon>{{ deployBlockReason(deployingEnv) }}
        </p>
        <el-form label-width="80px" class="deploy-form">
          <el-form-item label="版本号">
            <el-input v-model="deployVersion" placeholder="可选：commit hash / tag / 版本号" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDeploy" :loading="deploying" :disabled="deployingEnv && !isDeployReady(deployingEnv)">确认部署</el-button>
      </template>
    </el-dialog>

    <!-- 配置新增/编辑弹窗 -->
    <el-dialog v-model="configDialogVisible" :title="editingConfigId ? '编辑配置' : '新增配置'" width="520px" top="5vh" aria-labelledby="config-dialog-title">
      <el-form :model="configForm" label-width="80px">
        <el-form-item label="Key">
          <el-input v-model="configForm.key" placeholder="DATABASE_URL" :disabled="!!editingConfigId" />
        </el-form-item>
        <el-form-item label="Value">
          <el-input v-model="configForm.value" :type="configForm.is_encrypted ? 'password' : 'text'" :placeholder="configForm.is_encrypted ? '敏感值将加密存储' : '配置值'" />
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="configForm.env_id" placeholder="全局（所有环境）" clearable class="dialog-select-full">
            <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="加密">
          <el-switch v-model="configForm.is_encrypted" />
          <span class="config-hint">加密字段存储后不回显明文</span>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="configForm.description" placeholder="配置项说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfig" :loading="configSaving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 部署构建版本弹窗 -->
    <el-dialog v-model="deployBuildDialogVisible" title="部署构建版本" width="520px" top="5vh" aria-labelledby="deploy-build-dialog-title">
      <div v-if="deployingBuild" class="deploy-build-confirm">
        <p>应用：<strong>{{ app.name }}</strong></p>
        <p>构建版本：<code>{{ deployingBuild.build_number }}</code></p>
        <p v-if="deployingBuild.tag">标签：<el-tag size="small" type="warning">{{ deployingBuild.tag }}</el-tag></p>
        <p v-if="deployingBuild.commit">Commit：<code>{{ deployingBuild.commit.substring(0, 7) }}</code></p>
        <el-form label-width="80px" class="deploy-form">
          <el-form-item label="部署环境">
            <el-select v-model="deployBuildEnvId" placeholder="请选择环境" class="dialog-select-full">
              <el-option
                v-for="ae in appEnvs"
                :key="ae.env_id"
                :label="`${ae.env_name}${ae.approval_required ? ' (需审批)' : ''}`"
                :value="ae.env_id"
                :disabled="!ae.enabled"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="deployBuildDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDeployBuild" :loading="deploying" :disabled="!deployBuildEnvId">确认部署</el-button>
      </template>
    </el-dialog>

    <!-- 构建比较弹窗 -->
    <el-dialog v-model="showCompareDialog" title="构建版本比较" width="680px" top="5vh" aria-labelledby="compare-dialog-title">
      <div class="compare-content">
        <div class="compare-selectors">
          <el-select v-model="compareBuildA" placeholder="选择构建版本 A" filterable style="width: 260px">
            <el-option
              v-for="b in builds"
              :key="b.build_number"
              :label="`#${b.build_number}${b.tag ? ' [' + b.tag + ']' : ''}`"
              :value="b.build_number"
            />
          </el-select>
          <span class="compare-arrow">→</span>
          <el-select v-model="compareBuildB" placeholder="选择构建版本 B" filterable style="width: 260px">
            <el-option
              v-for="b in builds"
              :key="b.build_number"
              :label="`#${b.build_number}${b.tag ? ' [' + b.tag + ']' : ''}`"
              :value="b.build_number"
            />
          </el-select>
          <el-button type="primary" @click="handleCompare" :loading="compareLoading">比较</el-button>
        </div>

        <div v-if="compareResult" class="compare-result">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="属性">
              <div class="compare-label">版本 A: #{{ compareResult.build_a.build_number }}</div>
            </el-descriptions-item>
            <el-descriptions-item label="">
              <div class="compare-label">版本 B: #{{ compareResult.build_b.build_number }}</div>
            </el-descriptions-item>

            <el-descriptions-item label="标签">
              <el-tag v-if="compareResult.build_a.tag" size="small" type="warning">{{ compareResult.build_a.tag }}</el-tag>
              <span v-else class="text-muted">—</span>
            </el-descriptions-item>
            <el-descriptions-item label="标签">
              <el-tag v-if="compareResult.build_b.tag" size="small" type="warning">{{ compareResult.build_b.tag }}</el-tag>
              <span v-else class="text-muted">—</span>
            </el-descriptions-item>

            <el-descriptions-item label="Commit">
              <code v-if="compareResult.build_a.commit" class="commit-text">{{ compareResult.build_a.commit.substring(0, 7) }}</code>
              <span v-else class="text-muted">—</span>
            </el-descriptions-item>
            <el-descriptions-item label="Commit">
              <code v-if="compareResult.build_b.commit" class="commit-text">{{ compareResult.build_b.commit.substring(0, 7) }}</code>
              <span v-else class="text-muted">—</span>
            </el-descriptions-item>

            <el-descriptions-item label="分支">{{ compareResult.build_a.branch || '—' }}</el-descriptions-item>
            <el-descriptions-item label="分支">{{ compareResult.build_b.branch || '—' }}</el-descriptions-item>

            <el-descriptions-item label="产物大小">{{ formatSize(compareResult.build_a.artifact_size) }}</el-descriptions-item>
            <el-descriptions-item label="产物大小">
              {{ formatSize(compareResult.build_b.artifact_size) }}
              <el-tag :type="compareResult.diff.size_diff > 0 ? 'danger' : compareResult.diff.size_diff < 0 ? 'success' : 'info'" size="small" class="diff-tag">
                {{ compareResult.diff.size_diff_formatted }}
              </el-tag>
            </el-descriptions-item>

            <el-descriptions-item label="构建耗时">{{ formatDuration(compareResult.build_a.build_duration) }}</el-descriptions-item>
            <el-descriptions-item label="构建耗时">
              {{ formatDuration(compareResult.build_b.build_duration) }}
              <el-tag :type="compareResult.diff.duration_diff > 0 ? 'warning' : compareResult.diff.duration_diff < 0 ? 'success' : 'info'" size="small" class="diff-tag">
                {{ compareResult.diff.duration_diff_formatted }}
              </el-tag>
            </el-descriptions-item>

            <el-descriptions-item label="创建时间">{{ formatTime(compareResult.build_a.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatTime(compareResult.build_b.created_at) }}
              <span v-if="compareResult.diff.time_diff" class="time-diff">（{{ compareResult.diff.time_diff }}后）</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCompareDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 清理策略配置弹窗 -->
    <el-dialog v-model="showCleanupConfig" title="构建清理策略" width="480px" top="5vh" @open="fetchCleanupConfig" aria-labelledby="cleanup-config-title">
      <div class="cleanup-config">
        <el-form label-width="100px">
          <el-form-item label="保留数量">
            <el-input-number v-model="cleanupKeepCount" :min="1" :max="1000" />
            <span class="form-hint">保留最近 N 个构建记录</span>
          </el-form-item>
          <el-form-item label="保留天数">
            <el-input-number v-model="cleanupKeepDays" :min="1" :max="365" />
            <span class="form-hint">超过此天数的记录将被清理</span>
          </el-form-item>
        </el-form>
        <el-alert type="info" :closable="false" show-icon>
          <template #title>清理规则</template>
          <template #default>
            <ul class="cleanup-rules">
              <li>已固定（pinned）的构建不会被清理</li>
              <li>有版本标签（tag）的构建不会被清理</li>
              <li>清理策略为全局配置，对所有应用生效</li>
            </ul>
          </template>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="showCleanupConfig = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCleanupConfig" :loading="cleanupSaving">保存</el-button>
      </template>
    </el-dialog>

    <!-- Webhook 配置弹窗 -->
    <el-dialog v-model="showWebhookConfig" title="Webhook 配置" width="600px" top="5vh" @open="fetchWebhookConfig" aria-labelledby="webhook-config-title">
      <div class="webhook-config">
        <div class="webhook-section">
          <div class="webhook-section-title">Webhook URL</div>
          <div class="webhook-url-row">
            <el-input :value="webhookUrl" readonly>
              <template #append>
                <el-button @click="copyToClipboard(webhookUrl)">复制</el-button>
              </template>
            </el-input>
          </div>
          <div class="webhook-hint">将此 URL 配置到你的 CI/CD 系统中</div>
        </div>

        <div class="webhook-section">
          <div class="webhook-section-title">签名密钥</div>
          <div v-if="app.webhook_secret_configured" class="webhook-secret-info">
            <el-tag type="success" size="small">已配置</el-tag>
            <span class="webhook-hint">密钥已设置，用于验证 Webhook 请求的合法性</span>
          </div>
          <div v-else class="webhook-secret-info">
            <el-tag type="warning" size="small">未配置</el-tag>
            <span class="webhook-hint">建议生成密钥以确保安全</span>
          </div>
          <el-button type="primary" size="small" @click="handleGenerateSecret">
            {{ app.webhook_secret_configured ? '重新生成密钥' : '生成密钥' }}
          </el-button>
          <div v-if="webhookSecret" class="webhook-new-secret">
            <el-alert type="warning" :closable="false" show-icon>
              <template #title>
                新密钥已生成：<code>{{ webhookSecret }}</code>
                <el-button size="small" text @click="copyToClipboard(webhookSecret)">复制</el-button>
              </template>
              <template #default>请妥善保存此密钥，关闭后将无法再次查看</template>
            </el-alert>
          </div>
        </div>

        <div class="webhook-section">
          <div class="webhook-section-title">请求头说明</div>
          <div class="webhook-headers">
            <div class="webhook-header-item">
              <code>X-Webhook-Signature</code>
              <span>HMAC-SHA256 签名，格式 "sha256=xxx"</span>
            </div>
            <div class="webhook-header-item">
              <code>X-Build-Number</code>
              <span>构建号（可选，自动生成）</span>
            </div>
            <div class="webhook-header-item">
              <code>X-Build-Status</code>
              <span>构建状态：success / failed（默认 success）</span>
            </div>
            <div class="webhook-header-item">
              <code>X-Commit</code>
              <span>Git commit hash（可选）</span>
            </div>
            <div class="webhook-header-item">
              <code>X-Branch</code>
              <span>Git branch（可选）</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showWebhookConfig = false">关闭</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Warning, Download, UploadFilled, Lock, ArrowRight } from '@element-plus/icons-vue'
import { getDeployApp, deleteDeployApp, getAppEnvs, updateAppEnv, deleteAppEnv, executeDeploy, getDeployRecords, getDeployEnvs, getAppConfigs, createAppConfig, updateAppConfig, deleteAppConfig, uploadArtifact, deleteArtifact, getBuilds, deployBuild, deleteBuild, pinBuild, unpinBuild, generateWebhookSecret, getWebhookUrl, getCleanupConfig, updateCleanupConfig, cleanupBuilds, compareBuilds } from '@/api/deploy'
import { getAssets } from '@/api/assets'
import { getDockerHosts, getClusters } from '@/api/containers'

const route = useRoute()
const router = useRouter()
const appName = ref(String(route.params.name))
const activeTab = ref('overview')

// ── Tab 懒加载 ──
const loadedTabs = ref<Set<string>>(new Set(['overview']))

function handleTabChange(tab: string | number) {
  const tabStr = String(tab)
  if (loadedTabs.value.has(tabStr)) return
  loadedTabs.value.add(tabStr)
  if (tab === 'envs') {
    fetchEnvs()
    fetchEnvList()
    fetchDropdowns()
  } else if (tab === 'builds') {
    fetchBuilds()
  } else if (tab === 'history') {
    fetchRecords()
  } else if (tab === 'configs') {
    fetchConfigs()
    fetchEnvList()
  }
}

// ── 应用数据 ──
const app = ref<any>({})
async function fetchApp() {
  const res: any = await getDeployApp(appName.value)
  app.value = res.data
}

// ── 环境配置（含折叠状态） ──
const envLoading = ref(false)
const appEnvs = ref<any[]>([])
const collapsedEnvs = ref<Set<number>>(new Set())

function toggleEnvCard(envId: number) {
  const s = new Set(collapsedEnvs.value)
  if (s.has(envId)) s.delete(envId)
  else s.add(envId)
  collapsedEnvs.value = s
}

async function fetchEnvs() {
  envLoading.value = true
  try {
    const res: any = await getAppEnvs(appName.value)
    appEnvs.value = res.data
  } finally {
    envLoading.value = false
  }
}

// ── 下拉数据 ──
const assets = ref<any[]>([])
const dockerHosts = ref<any[]>([])
const k8sClusters = ref<any[]>([])

async function fetchDropdowns() {
  const [a, d, k] = await Promise.all([
    getAssets({ page_size: 200 }).catch(() => ({ data: { items: [] } })),
    getDockerHosts().catch(() => ({ data: [] })),
    getClusters().catch(() => ({ data: [] })),
  ])
  assets.value = (a as any).data?.items || []
  dockerHosts.value = (d as any).data || []
  k8sClusters.value = (k as any).data || []
}

// ── 部署历史（分页） ──
const recordsLoading = ref(false)
const records = ref<any[]>([])
const recordsPage = ref(1)
const recordsPageSize = 20
const recordsTotal = ref(0)
const statusLabelMap: Record<string, string> = { pending: '待执行', building: '构建中', deploying: '部署中', success: '成功', failed: '失败', cancelled: '已取消' }
const statusTypeMap: Record<string, 'info' | 'warning' | 'success' | 'danger'> = { pending: 'info', building: 'warning', deploying: 'warning', success: 'success', failed: 'danger', cancelled: 'info' }

const lastDeployLabel = computed(() => {
  if (!records.value.length) return '无'
  const r = records.value[0]
  return `${formatTime(r.created_at)} ${statusLabelMap[r.status] || r.status}`
})

async function fetchRecords() {
  recordsLoading.value = true
  try {
    const res: any = await getDeployRecords({ app_name: appName.value, page: recordsPage.value, page_size: recordsPageSize })
    records.value = res.data.items
    recordsTotal.value = res.data.total || 0
  } finally {
    recordsLoading.value = false
  }
}

// ── 构建历史（分页） ──
const buildsLoading = ref(false)
const builds = ref<any[]>([])
const buildsPage = ref(1)
const buildsPageSize = 20
const buildsTotal = ref(0)
const buildFilterStatus = ref('')
const buildSearch = ref('')
const showWebhookConfig = ref(false)
const webhookUrl = ref('')
const webhookSecret = ref('')

// 清理策略配置
const showCleanupConfig = ref(false)
const cleanupKeepCount = ref(20)
const cleanupKeepDays = ref(30)
const cleanupSaving = ref(false)

// 构建比较
const showCompareDialog = ref(false)
const compareBuildA = ref('')
const compareBuildB = ref('')
const compareResult = ref<any>(null)
const compareLoading = ref(false)

async function fetchBuilds() {
  buildsLoading.value = true
  try {
    const res: any = await getBuilds(appName.value, {
      status: buildFilterStatus.value,
      keyword: buildSearch.value,
      page: buildsPage.value,
      page_size: buildsPageSize,
    })
    builds.value = res.data.items
    buildsTotal.value = res.data.total || 0

    // 检查是否有 pending 状态的构建，如果有则启动轮询
    const hasPending = builds.value.some((b: any) => b.status === 'pending')
    if (hasPending) {
      startBuildsPolling()
    } else {
      stopBuildsPolling()
    }
  } finally {
    buildsLoading.value = false
  }
}

// ── 构建状态轮询 ──
let buildsPollTimer: ReturnType<typeof setInterval> | null = null

function startBuildsPolling() {
  if (buildsPollTimer) return // 已经在轮询
  buildsPollTimer = setInterval(() => {
    if (activeTab.value === 'builds') {
      fetchBuilds()
    } else {
      stopBuildsPolling()
    }
  }, 8000) // 8 秒轮询一次
}

function stopBuildsPolling() {
  if (buildsPollTimer) {
    clearInterval(buildsPollTimer)
    buildsPollTimer = null
  }
}

// ── 部署构建版本弹窗 ──
const deployBuildDialogVisible = ref(false)
const deployingBuild = ref<any>(null)
const deployBuildEnvId = ref<number | null>(null)

function openDeployBuildDialog(build: any) {
  deployingBuild.value = build
  deployBuildEnvId.value = null
  deployBuildDialogVisible.value = true
}

async function handleDeployBuild() {
  if (!deployBuildEnvId.value) {
    ElMessage.warning('请选择部署环境')
    return
  }
  deploying.value = true
  try {
    const res: any = await deployBuild(appName.value, deployingBuild.value.build_number, {
      app_name: appName.value,
      env_id: deployBuildEnvId.value,
    })
    ElMessage.success('部署已触发')
    deployBuildDialogVisible.value = false
    router.push(`/deploy/records/${res.data.id}`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '部署触发失败')
  } finally {
    deploying.value = false
  }
}

async function handleDeleteBuild(buildNumber: string) {
  try {
    await deleteBuild(appName.value, buildNumber)
    ElMessage.success('已删除')
    fetchBuilds()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function togglePin(build: any) {
  try {
    if (build.is_pinned) {
      await unpinBuild(appName.value, build.build_number)
      ElMessage.success('已取消固定')
    } else {
      await pinBuild(appName.value, build.build_number)
      ElMessage.success('已固定')
    }
    fetchBuilds()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

// ── Webhook 配置 ──
async function fetchWebhookConfig() {
  try {
    const res: any = await getWebhookUrl(appName.value)
    webhookUrl.value = res.data.webhook_url
  } catch (e: any) {
    ElMessage.error('获取 Webhook URL 失败')
  }
}

async function handleGenerateSecret() {
  try {
    const res: any = await generateWebhookSecret(appName.value)
    webhookSecret.value = res.data.secret
    ElMessage.success('密钥已生成，请妥善保存')
    fetchApp() // 刷新应用信息
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '生成密钥失败')
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// ── 清理策略配置 ──
async function fetchCleanupConfig() {
  try {
    const res: any = await getCleanupConfig(appName.value)
    cleanupKeepCount.value = res.data.keep_count
    cleanupKeepDays.value = res.data.keep_days
  } catch (e: any) {
    ElMessage.error('获取清理配置失败')
  }
}

async function handleSaveCleanupConfig() {
  cleanupSaving.value = true
  try {
    await updateCleanupConfig(appName.value, {
      keep_count: cleanupKeepCount.value,
      keep_days: cleanupKeepDays.value,
    })
    ElMessage.success('配置已保存')
    showCleanupConfig.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    cleanupSaving.value = false
  }
}

async function handleCleanupBuilds() {
  try {
    const res: any = await cleanupBuilds(appName.value)
    ElMessage.success(res.msg || '清理完成')
    fetchBuilds()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '清理失败')
  }
}

// ── 构建比较 ──
function openCompareDialog() {
  compareBuildA.value = ''
  compareBuildB.value = ''
  compareResult.value = null
  showCompareDialog.value = true
}

async function handleCompare() {
  if (!compareBuildA.value || !compareBuildB.value) {
    ElMessage.warning('请选择两个构建版本')
    return
  }
  if (compareBuildA.value === compareBuildB.value) {
    ElMessage.warning('请选择不同的构建版本')
    return
  }
  compareLoading.value = true
  try {
    const res: any = await compareBuilds(appName.value, compareBuildA.value, compareBuildB.value)
    compareResult.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '比较失败')
  } finally {
    compareLoading.value = false
  }
}

// ── 配置管理（带搜索） ──
const configsLoading = ref(false)
const configs = ref<any[]>([])
const envList = ref<any[]>([])
const configDialogVisible = ref(false)
const editingConfigId = ref<number | null>(null)
const configSaving = ref(false)
const configSearch = ref('')
const configForm = reactive({
  key: '',
  value: '',
  env_id: null as number | null,
  is_encrypted: false,
  description: '',
})

const filteredConfigs = computed(() => {
  if (!configSearch.value.trim()) return configs.value
  const q = configSearch.value.toLowerCase()
  return configs.value.filter(c =>
    c.key.toLowerCase().includes(q) || (c.description || '').toLowerCase().includes(q)
  )
})

async function fetchConfigs() {
  configsLoading.value = true
  try {
    const res: any = await getAppConfigs(appName.value)
    configs.value = res.data
  } finally {
    configsLoading.value = false
  }
}

async function fetchEnvList() {
  const res: any = await getDeployEnvs().catch(() => ({ data: [] }))
  envList.value = res.data || []
}

function openConfigDialog(row?: any) {
  editingConfigId.value = row?.id || null
  Object.assign(configForm, row ? {
    key: row.key,
    value: row.is_encrypted ? '' : row.value,
    env_id: row.env_id,
    is_encrypted: row.is_encrypted,
    description: row.description,
  } : { key: '', value: '', env_id: null, is_encrypted: false, description: '' })
  configDialogVisible.value = true
}

async function handleSaveConfig() {
  if (!configForm.key.trim()) {
    ElMessage.warning('请输入 Key')
    return
  }
  configSaving.value = true
  try {
    if (editingConfigId.value) {
      await updateAppConfig(editingConfigId.value, { ...configForm })
    } else {
      await createAppConfig(appName.value, { ...configForm })
    }
    ElMessage.success('保存成功')
    configDialogVisible.value = false
    fetchConfigs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    configSaving.value = false
  }
}

async function handleDeleteConfig(id: number) {
  try {
    await deleteAppConfig(id)
    ElMessage.success('已删除')
    fetchConfigs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ── 添加环境弹窗 ──
const addEnvDialogVisible = ref(false)
const addEnvId = ref<number | null>(null)
const addEnvLoading = ref(false)

const availableEnvs = computed(() => {
  const existingIds = new Set(appEnvs.value.map((ae: any) => ae.env_id))
  return envList.value.filter((e: any) => !existingIds.has(e.id))
})

function openAddEnvDialog() {
  addEnvId.value = null
  addEnvDialogVisible.value = true
}

async function handleAddEnv() {
  if (!addEnvId.value) {
    ElMessage.warning('请选择环境')
    return
  }
  addEnvLoading.value = true
  try {
    await updateAppEnv(appName.value, addEnvId.value, { enabled: true })
    ElMessage.success('添加成功')
    addEnvDialogVisible.value = false
    fetchEnvs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  } finally {
    addEnvLoading.value = false
  }
}

// ── 环境配置弹窗 ──
const envDialogVisible = ref(false)
const editingEnv = ref<any>(null)
const envSaving = ref(false)
const envForm = reactive<any>({
  enabled: true,
  ssh_asset_id: null,
  deploy_path: '',
  deploy_script: '',
  health_check_url: '',
  health_check_port: 0,
  health_check_timeout: 30,
  docker_host_id: null,
  docker_image: '',
  docker_container_name: '',
  docker_ports: '',
  docker_env_vars: '',
  docker_network: '',
  docker_extra_args: '',
  k8s_cluster_id: null,
  k8s_namespace: 'default',
  k8s_deployment: '',
  k8s_container_name: '',
})

function openEnvDialog(ae: any) {
  editingEnv.value = ae
  Object.assign(envForm, {
    enabled: ae.enabled,
    ssh_asset_id: ae.ssh_asset_id,
    deploy_path: ae.deploy_path,
    deploy_script: ae.deploy_script,
    health_check_url: ae.health_check_url || '',
    health_check_port: ae.health_check_port || 0,
    health_check_timeout: ae.health_check_timeout || 30,
    docker_host_id: ae.docker_host_id,
    docker_image: ae.docker_image,
    docker_container_name: ae.docker_container_name,
    docker_ports: ae.docker_ports,
    docker_env_vars: ae.docker_env_vars,
    docker_network: ae.docker_network,
    docker_extra_args: ae.docker_extra_args,
    k8s_cluster_id: ae.k8s_cluster_id,
    k8s_namespace: ae.k8s_namespace,
    k8s_deployment: ae.k8s_deployment,
    k8s_container_name: ae.k8s_container_name,
  })
  envDialogVisible.value = true
}

async function handleSaveEnv() {
  envSaving.value = true
  try {
    await updateAppEnv(appName.value, editingEnv.value.env_id, { ...envForm })
    ElMessage.success('保存成功')
    envDialogVisible.value = false
    fetchEnvs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    envSaving.value = false
  }
}

async function handleDelete() {
  try {
    await deleteDeployApp(appName.value)
    ElMessage.success('删除成功')
    router.push('/deploy/apps')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleRemoveEnv(envId: number) {
  try {
    await deleteAppEnv(appName.value, envId)
    ElMessage.success('已移除')
    fetchEnvs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '移除失败')
  }
}

// ── 部署弹窗（含前置检查） ──
const deployDialogVisible = ref(false)
const deployingEnv = ref<any>(null)
const deployVersion = ref('')
const deploying = ref(false)

function isDeployReady(ae: any): boolean {
  if (app.value.build_mode === 'jenkins') return true
  return !!ae.artifact_filename
}

function deployBlockReason(ae: any): string {
  if (app.value.build_mode !== 'jenkins' && !ae.artifact_filename) return '尚未上传构建产物，无法部署'
  return ''
}

function openDeployDialog(ae: any) {
  deployingEnv.value = ae
  deployVersion.value = ''
  deployDialogVisible.value = true
}

async function handleDeploy() {
  if (deployingEnv.value && !isDeployReady(deployingEnv.value)) {
    ElMessage.warning(deployBlockReason(deployingEnv.value))
    return
  }
  deploying.value = true
  try {
    const res: any = await executeDeploy({
      app_name: appName.value,
      env_id: deployingEnv.value.env_id,
      version: deployVersion.value,
    })
    ElMessage.success('部署已触发')
    deployDialogVisible.value = false
    router.push(`/deploy/records/${res.data.id}`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '部署触发失败')
  } finally {
    deploying.value = false
  }
}

// ── 构建产物（环境级别） ──
const uploadingEnvId = ref<number | null>(null)

async function handleUploadArtifact(envId: number, file: File) {
  uploadingEnvId.value = envId
  try {
    await uploadArtifact(appName.value, envId, file)
    ElMessage.success('上传成功')
    fetchEnvs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploadingEnvId.value = null
  }
  return false
}

async function handleDeleteArtifact(envId: number) {
  try {
    await deleteArtifact(appName.value, envId)
    ElMessage.success('已删除')
    fetchEnvs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

function handleDownloadArtifact(ae: any) {
  const token = localStorage.getItem('token')
  const url = `/api/v1/deploy/apps/${appName.value}/envs/${ae.env_id}/artifact/download`
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => {
      if (!res.ok) throw new Error('下载失败')
      return res.blob()
    })
    .then(blob => {
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = ae.artifact_filename || 'artifact'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    })
    .catch(() => ElMessage.error('下载失败'))
}

// ── 辅助 ──
const typeLabel = (v: string) => ({ web: 'Web 应用', api: 'API 服务', worker: '后台任务', frontend: '前端项目', other: '其他' }[v] || v)
const strategyLabel = (v: string) => ({ ssh: 'SSH', docker: 'Docker', k8s: 'Kubernetes' }[v] || v)
const strategyType = (v: string) => ({ ssh: '', docker: 'warning', k8s: 'danger' }[v] || '') as any

function buildModeLabel(mode: string) {
  return { upload: '文件上传', webhook: 'Webhook', jenkins: 'Jenkins' }[mode] || mode
}

function buildModeDetail(app: any) {
  if (app.build_mode === 'jenkins') return app.jenkins_job_name || '—'
  if (app.build_mode === 'webhook') return app.webhook_secret_configured ? '已配置密钥' : '未配置密钥'
  return app.build_command || '—'
}

function formatTime(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} 字节`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDuration(sec: number) {
  if (sec < 60) return `${Math.round(sec)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}

// ── 初始化（keep-alive: onActivated） ──
onActivated(() => {
  appName.value = String(route.params.name)
  activeTab.value = 'overview'
  loadedTabs.value = new Set(['overview'])
  collapsedEnvs.value = new Set()
  fetchApp()
})

onDeactivated(() => {
  stopBuildsPolling()
})
</script>

<style scoped>
.page-breadcrumb {
  margin-bottom: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.detail-tabs {
  margin-top: 4px;
}

/* ── KPI 摘要卡片 ── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 14px 16px;
}

.kpi-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.kpi-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.kpi-number {
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.kpi-text {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
}

/* ── 环境工具栏 ── */
.env-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.config-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.config-search {
  max-width: 260px;
}

/* ── 空状态插图 ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
}

.empty-illustration {
  width: 160px;
  height: auto;
  opacity: 0.7;
}

.empty-illustration-sm {
  width: 120px;
  height: auto;
  opacity: 0.6;
}

.empty-text {
  font-size: 14px;
  color: var(--text-muted);
}

/* ── 环境卡片（含折叠） ── */
.env-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 16px;
  overflow: hidden;
}

.env-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: color-mix(in srgb, var(--primary-color) 6%, transparent);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
}

.env-card-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.env-collapse-icon {
  transition: transform 200ms ease-out;
  color: var(--text-muted);
  font-size: 14px;
}

.env-collapse-icon.collapsed {
  transform: rotate(0deg);
}

.env-collapse-icon:not(.collapsed) {
  transform: rotate(90deg);
}

.env-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.env-card-body {
  padding: 16px 20px;
  display: grid;
  grid-template-rows: 1fr;
  transition: grid-template-rows 200ms ease-out, padding 200ms ease-out;
  overflow: hidden;
}

.env-card-body.collapsed {
  grid-template-rows: 0fr;
  padding-top: 0;
  padding-bottom: 0;
}

.env-field {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  line-height: 1.6;
}

.env-field:last-child {
  margin-bottom: 0;
}

.env-field-label {
  color: var(--text-muted);
  margin-right: 4px;
}

.form-hint {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.env-field code {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
  word-break: break-all;
}

/* ── 部署确认 ── */
.deploy-confirm p {
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.deploy-env-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  margin: 8px 0;
  background: var(--bg-color);
  border-radius: var(--border-radius);
  font-size: 13px;
  color: var(--text-secondary);
}

.deploy-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--warning-color);
  font-size: 13px;
}

.deploy-form {
  margin-top: 16px;
}

.version-text {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
}

:deep(.clickable-row) {
  cursor: pointer;
}

:deep(.clickable-row:focus-visible) {
  outline: 2px solid var(--primary-color);
  outline-offset: -2px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ── 配置管理 ── */
.config-key {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: var(--primary-color);
}

.config-value {
  font-size: 13px;
  color: var(--text-secondary);
  word-break: break-all;
}

.config-encrypted {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 2px;
}

.config-encrypted-icon {
  color: var(--warning-color);
}

.config-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ── 弹窗通用 ── */
.dialog-select-full {
  width: 100%;
}

.input-number-200 {
  width: 200px;
}

/* ── 构建产物 ── */
.env-artifact-divider {
  margin: 12px 0;
  border-top: 1px dashed var(--border-color);
}

.env-artifact-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.env-artifact-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.env-artifact-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.env-artifact-icon {
  color: var(--primary-color);
  flex-shrink: 0;
}

.env-artifact-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-all;
}

.env-artifact-meta {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.env-artifact-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.env-artifact-empty {
  display: flex;
  align-items: center;
  gap: 12px;
}

.env-artifact-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .env-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .env-card-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .config-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .config-search {
    max-width: 100%;
  }

  .env-artifact-file {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .env-collapse-icon,
  .env-card-body {
    transition: none;
  }
}

/* ── 构建历史 ── */
.build-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
}

.build-filters {
  display: flex;
  gap: 8px;
}

.build-number {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: var(--primary-color);
}

.commit-text {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: var(--text-primary);
}

.text-muted {
  color: var(--text-muted);
}

.deploy-build-confirm p {
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

/* ── Webhook 配置 ── */
.webhook-config {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.webhook-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.webhook-url-row {
  margin-bottom: 8px;
}

.webhook-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.webhook-secret-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.webhook-new-secret {
  margin-top: 12px;
}

.webhook-headers {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.webhook-header-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.webhook-header-item code {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: var(--primary-color);
  min-width: 160px;
}

/* ── 清理策略 ── */
.build-actions {
  display: flex;
  gap: 8px;
}

.cleanup-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cleanup-rules {
  margin: 8px 0 0;
  padding-left: 20px;
  font-size: 13px;
}

.cleanup-rules li {
  margin-bottom: 4px;
}

/* ── 构建比较 ── */
.compare-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.compare-selectors {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.compare-arrow {
  font-size: 18px;
  color: var(--text-muted);
}

.compare-result {
  margin-top: 8px;
}

.compare-label {
  font-weight: 600;
  color: var(--text-primary);
}

.diff-tag {
  margin-left: 8px;
}

.time-diff {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 4px;
}

@media (max-width: 768px) {
  .build-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .build-filters {
    flex-direction: column;
  }
}
</style>
