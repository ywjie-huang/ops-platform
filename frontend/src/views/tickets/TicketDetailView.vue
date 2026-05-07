<template>
  <div>
    <div class="page-header"><h2 class="page-title">工单详情</h2><el-button text @click="$router.back()">← 返回</el-button></div>
    <div class="data-card" v-if="ticket">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题"><strong>{{ ticket.title }}</strong></el-descriptions-item>
        <el-descriptions-item label="优先级"><el-tag :type="priorityType(ticket.priority)" size="small">{{ ticket.priority }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="statusType(ticket.status)" size="small">{{ ticket.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="指派人">{{ ticket.assignee || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ ticket.created_at }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ ticket.updated_at }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ ticket.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'; import { useRoute } from 'vue-router'; import { getTicket } from '@/api/tickets'
const route = useRoute(); const ticket = ref<any>(null)
const priorityType = (p: string) => ({ low: 'info', normal: '', high: 'warning', critical: 'danger' }[p] || '') as any
const statusType = (s: string) => ({ open: 'primary', in_progress: 'warning', resolved: 'success', closed: 'info' }[s] || '') as any
onMounted(async () => { const res: any = await getTicket(Number(route.params.id)); ticket.value = res.data })
</script>
