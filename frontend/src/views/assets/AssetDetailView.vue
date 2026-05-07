<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">资产详情</h2>
      <el-button text @click="$router.back()">← 返回</el-button>
    </div>
    <div class="data-card" v-loading="loading" v-if="asset">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="名称"><strong>{{ asset.name }}</strong></el-descriptions-item>
        <el-descriptions-item label="类型">{{ asset.asset_type }}</el-descriptions-item>
        <el-descriptions-item label="IP">{{ asset.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="asset.status === '在线' ? 'success' : asset.status === '离线' ? 'danger' : 'warning'">{{ asset.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="负责人">{{ asset.owner || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ asset.created_at }}</el-descriptions-item>
        <el-descriptions-item label="说明" :span="2">{{ asset.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset } from '@/api/assets'

const route = useRoute()
const asset = ref<any>(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res: any = await getAsset(Number(route.params.id))
    asset.value = res.data
  } finally { loading.value = false }
})
</script>
