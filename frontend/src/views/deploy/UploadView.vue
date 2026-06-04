<template>
  <div>
    <div class="page-header"><h2 class="page-title">文件上传</h2></div>
    <div class="data-card">
      <el-form :model="form" label-width="100px" style="max-width: 600px;">
        <el-form-item label="目标主机">
          <el-select v-model="form.asset_id" placeholder="选择主机" style="width: 100%;" filterable>
            <el-option v-for="a in assets" :key="a.id" :label="`${a.name} (${a.ip_address})`" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标目录">
          <el-input v-model="form.dir_path" placeholder="/opt/apps/" />
        </el-form-item>
        <el-form-item label="文件">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :on-exceed="() => ElMessage.warning('只能上传一个文件')"
            :file-list="fileList"
            drag
          >
            <el-icon style="font-size: 40px; color: var(--text-muted);"><Upload /></el-icon>
            <div style="color: var(--text-muted);">拖拽文件到此处，或<em>点击选择</em></div>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleUpload" :loading="uploading" :disabled="!canUpload">上传</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 上传结果 -->
    <div v-if="result" class="data-card" style="margin-top: 16px;">
      <el-result :icon="result.ok ? 'success' : 'error'" :title="result.ok ? '上传成功' : '上传失败'">
        <template #sub-title>
          <div v-if="result.ok">
            <p>远程路径：{{ result.path }}</p>
            <p>文件大小：{{ formatSize(result.size) }}</p>
          </div>
          <p v-else>{{ result.error }}</p>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onActivated } from 'vue'
import { getAssets } from '@/api/assets'
import { sftpUpload } from '@/api/sftp'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'

const assets = ref<any[]>([])
const fileList = ref<any[]>([])
const uploading = ref(false)
const result = ref<{ ok: boolean; path?: string; size?: number; error?: string } | null>(null)

const form = reactive({
  asset_id: null as number | null,
  dir_path: '/opt/apps/',
})

const canUpload = computed(() => form.asset_id && form.dir_path && fileList.value.length > 0)

async function fetchAssets() {
  const res: any = await getAssets({ page: 1, page_size: 1000 })
  assets.value = res.data?.items || res.data || []
}

function onFileChange(file: any) {
  fileList.value = file ? [file] : []
}

async function handleUpload() {
  if (!canUpload.value) return
  uploading.value = true
  result.value = null
  try {
    const file = fileList.value[0]?.raw
    const res: any = await sftpUpload(form.asset_id!, form.dir_path, file)
    result.value = { ok: true, path: res.data?.path, size: res.data?.size }
  } catch (e: any) {
    result.value = { ok: false, error: e?.response?.data?.detail || e?.message || '上传失败' }
  } finally {
    uploading.value = false
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onActivated(fetchAssets)
</script>

<style scoped>
.data-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 24px; }
</style>
