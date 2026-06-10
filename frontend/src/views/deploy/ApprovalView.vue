<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">部署审批</h2>
    </div>

    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="app_name" label="应用" min-width="120" />
        <el-table-column prop="env_name" label="环境" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.env_name || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="版本/构建" min-width="180">
          <template #default="{ row }">
            <div class="version-info">
              <code v-if="row.version" class="version-text">{{ row.version }}</code>
              <template v-if="row.build_number">
                <el-tag v-if="row.build_tag" size="small" type="warning">{{ row.build_tag }}</el-tag>
                <code v-if="row.build_commit" class="commit-text">{{ row.build_commit.substring(0, 7) }}</code>
              </template>
              <span v-if="!row.version && !row.build_number" class="text-muted">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_user_name" label="触发人" width="90" />
        <el-table-column prop="trigger_type" label="触发方式" width="90">
          <template #default="{ row }">{{ { manual: '手动', rollback: '回滚', webhook: 'Webhook' }[row.trigger_type] || row.trigger_type }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="{ pending: 'warning', approved: 'success', rejected: 'danger' }[row.status]" size="small">
              {{ { pending: '待审批', approved: '已通过', rejected: '已拒绝' }[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="primary" @click="handleApprove(row)">通过</el-button>
              <el-button size="small" type="danger" @click="openRejectDialog(row)">拒绝</el-button>
            </template>
            <template v-else>
              <span class="resolved-info">
                {{ row.approver_name || '—' }}
                <template v-if="row.comment">（{{ row.comment }}）</template>
              </span>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && items.length === 0" description="暂无审批记录" />
    </div>

    <!-- 拒绝弹窗 -->
    <el-dialog v-model="rejectDialogVisible" title="拒绝审批" width="440px">
      <p class="reject-info">确认拒绝 <strong>{{ rejectingItem?.app_name }}</strong> 在 <strong>{{ rejectingItem?.env_name }}</strong> 的部署？</p>
      <el-form label-width="60px">
        <el-form-item label="原因">
          <el-input v-model="rejectComment" type="textarea" :rows="3" placeholder="拒绝原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleReject" :loading="rejecting">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeployApprovals, approveDeploy, rejectDeploy } from '@/api/deploy'

const loading = ref(false)
const items = ref<any[]>([])

const rejectDialogVisible = ref(false)
const rejectingItem = ref<any>(null)
const rejectComment = ref('')
const rejecting = ref(false)

function formatTime(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchData() {
  loading.value = true
  try {
    // 获取待审批 + 已处理的（最近 50 条）
    const [pending, resolved] = await Promise.all([
      getDeployApprovals({ status: 'pending' }).catch(() => ({ data: [] })),
      getDeployApprovals({ status: '' }).catch(() => ({ data: [] })),
    ])
    // 合并：待审批优先，再按时间倒序
    const all = [...((pending as any).data || []), ...((resolved as any).data || [])]
    // 去重（pending 可能出现在两个结果中）
    const seen = new Set()
    items.value = all.filter((a: any) => {
      if (seen.has(a.id)) return false
      seen.add(a.id)
      return true
    }).slice(0, 50)
  } finally {
    loading.value = false
  }
}

async function handleApprove(row: any) {
  await approveDeploy(row.id)
  ElMessage.success('审批通过，部署已触发')
  fetchData()
}

function openRejectDialog(row: any) {
  rejectingItem.value = row
  rejectComment.value = ''
  rejectDialogVisible.value = true
}

async function handleReject() {
  rejecting.value = true
  try {
    await rejectDeploy(rejectingItem.value.id, rejectComment.value)
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    fetchData()
  } finally {
    rejecting.value = false
  }
}

onActivated(fetchData)
</script>

<style scoped>
.version-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.version-text {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
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

.resolved-info {
  font-size: 12px;
  color: var(--text-muted);
}

.reject-info {
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}
</style>
