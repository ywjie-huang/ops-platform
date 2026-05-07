<template>
  <div>
    <div class="page-header"><h2 class="page-title">主机监控</h2></div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="name" label="主机"><template #default="{row}"><strong>{{ row.name }}</strong><br><span style="color:var(--text-muted);font-size:12px">{{ row.ip_address }}</span></template></el-table-column>
        <el-table-column label="CPU" width="100"><template #default="{row}"><el-progress :percentage="row.cpu" :color="cpuColor(row.cpu)" :stroke-width="10" /></template></el-table-column>
        <el-table-column label="内存" width="100"><template #default="{row}"><el-progress :percentage="row.memory" :color="cpuColor(row.memory)" :stroke-width="10" /></template></el-table-column>
        <el-table-column label="磁盘" width="100"><template #default="{row}"><el-progress :percentage="row.disk" :color="cpuColor(row.disk)" :stroke-width="10" /></template></el-table-column>
        <el-table-column prop="network_in" label="入站" width="90" />
        <el-table-column prop="network_out" label="出站" width="90" />
        <el-table-column prop="owner" label="负责人" width="90" />
        <el-table-column label="操作" width="80">
          <template #default="{row}"><el-button size="small" text type="primary" @click="$router.push(`/monitoring/hosts/${row.id}`)">详情</el-button></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'; import { getHosts } from '@/api/monitoring'
const loading = ref(false); const items = ref<any[]>([])
const cpuColor = (v: number) => v > 90 ? '#ef4444' : v > 70 ? '#f59e0b' : '#22c55e'
onMounted(async () => { loading.value = true; try { const res: any = await getHosts(); items.value = res.data } finally { loading.value = false } })
</script>
