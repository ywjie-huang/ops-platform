<template>
  <div>
    <div class="page-header"><h2 class="page-title">主机详情</h2><el-button text @click="$router.back()">← 返回</el-button></div>
    <div class="data-card" v-if="host">
      <el-row :gutter="20">
        <el-col :span="8" v-for="g in gauges" :key="g.label">
          <div style="text-align:center;padding:20px">
            <el-progress type="circle" :percentage="g.value" :color="gaugeColor(g.value)" :width="120" />
            <div style="margin-top:8px;font-weight:600">{{ g.label }}</div>
          </div>
        </el-col>
      </el-row>
      <el-descriptions :column="2" border style="margin-top:20px">
        <el-descriptions-item label="主机名">{{ host.name }}</el-descriptions-item>
        <el-descriptions-item label="IP">{{ host.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ host.owner || '-' }}</el-descriptions-item>
        <el-descriptions-item label="系统">{{ host.os || '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'; import { useRoute } from 'vue-router'; import { getHostDetail } from '@/api/monitoring'
const route = useRoute(); const host = ref<any>(null)
const gauges = computed(() => host.value ? [
  { label: 'CPU', value: host.value.cpu_percent || 0 },
  { label: '内存', value: host.value.memory_percent || 0 },
  { label: '磁盘', value: host.value.disk_percent || 0 },
  { label: '负载', value: Math.min(Math.round((host.value.load_avg || 0) * 20), 100) },
] : [])
const gaugeColor = (v: number) => v > 90 ? '#ef4444' : v > 70 ? '#f59e0b' : '#22c55e'
onMounted(async () => { const res: any = await getHostDetail(Number(route.params.id)); host.value = res.data })
</script>
