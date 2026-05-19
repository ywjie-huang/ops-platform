<template>
  <div class="report-center">
    <div class="page-header">
      <h2 class="page-title">📊 报表中心</h2>
      <p class="page-subtitle">查看系统预置报表，掌握运维数据全貌</p>
    </div>

    <div v-loading="loading" class="report-grid">
      <div
        v-for="report in reports"
        :key="report.id"
        class="report-card"
        @click="viewReport(report.id)"
      >
        <div class="card-icon">{{ report.icon }}</div>
        <div class="card-body">
          <h3 class="card-title">{{ report.name }}</h3>
          <p class="card-desc">{{ report.description }}</p>
        </div>
        <div class="card-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && !reports.length" description="暂无可用报表" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import { getPresetReports } from '@/api/reports'

const router = useRouter()
const reports = ref<any[]>([])
const loading = ref(true)

function viewReport(id: string) {
  router.push(`/reports/${id}`)
}

onMounted(async () => {
  try {
    const res: any = await getPresetReports()
    reports.value = res.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.report-center { max-width: 1200px; }

.page-header {
  margin-bottom: 28px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 6px;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.report-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px 24px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.1);
    transform: translateY(-1px);

    .card-arrow { opacity: 1; transform: translateX(0); color: #3b82f6; }
  }
}

.card-icon {
  font-size: 36px;
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f9ff 0%, #dbeafe 100%);
  border-radius: 12px;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.card-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

.card-arrow {
  flex-shrink: 0;
  opacity: 0;
  transform: translateX(-4px);
  transition: all 0.2s ease;
  color: var(--text-muted);
}

@media (max-width: 600px) {
  .report-grid { grid-template-columns: 1fr; }
}
</style>
