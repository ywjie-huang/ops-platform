<template>
  <div>
    <div class="page-header"><h2 class="page-title">报表中心</h2></div>
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :md="8" v-for="report in reports" :key="report.id">
        <div class="data-card report-card" @click="viewReport(report.id)">
          <div class="report-icon">📊</div>
          <h3>{{ report.name }}</h3>
          <p>{{ report.description }}</p>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'; import { useRouter } from 'vue-router'; import { getPresetReports } from '@/api/reports'
const router = useRouter(); const reports = ref<any[]>([])
function viewReport(id: string) { router.push(`/reports/${id}`) }
onMounted(async () => { const res: any = await getPresetReports(); reports.value = res.data })
</script>

<style scoped>.report-card { cursor: pointer; text-align: center; transition: box-shadow 0.2s; &:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); } }
.report-icon { font-size: 36px; margin-bottom: 8px; } h3 { margin-bottom: 4px; } p { color: var(--text-muted); font-size: 13px; }</style>
