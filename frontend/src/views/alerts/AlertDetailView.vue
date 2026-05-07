<template>
  <div>
    <div class="page-header"><h2 class="page-title">告警详情</h2><el-button text @click="$router.back()">← 返回</el-button></div>
    <div class="data-card" v-if="alert">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题"><strong>{{ alert.title }}</strong></el-descriptions-item>
        <el-descriptions-item label="级别"><el-tag :type="levelType(alert.level)" size="small">{{ alert.level }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="statusType(alert.status)" size="small">{{ alert.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="来源">{{ alert.source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ alert.created_at }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ alert.updated_at }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ alert.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'; import { useRoute } from 'vue-router'; import { getAlert } from '@/api/alerts'
const route = useRoute(); const alert = ref<any>(null)
const levelType = (l: string) => ({ low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }[l] || '') as any
const statusType = (s: string) => ({ pending: 'warning', confirmed: 'primary', resolved: 'success', ignored: 'info' }[s] || '') as any
onMounted(async () => { const res: any = await getAlert(Number(route.params.id)); alert.value = res.data })
</script>
