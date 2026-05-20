<template>
  <el-dialog :model-value="visible" @update:model-value="$emit('update:visible', $event)"
    :title="`编辑: ${filePath}`" width="80%" top="5vh" destroy-on-close>
    <div v-loading="editLoading">
      <el-input v-model="editContent" type="textarea" :rows="28" :autosize="false"
        style="font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px;" />
    </div>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="editSaving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { sftpRead, sftpWrite } from '@/api/sftp'

const props = defineProps<{
  visible: boolean
  filePath: string
  assetId: number
  currentKeyId: number | undefined
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  saved: []
}>()

const editContent = ref('')
const editLoading = ref(false)
const editSaving = ref(false)

watch(() => props.visible, async (val) => {
  if (!val || !props.filePath) return
  editLoading.value = true
  editContent.value = ''
  try {
    const res: any = await sftpRead(props.assetId, props.filePath, props.currentKeyId)
    editContent.value = res.data.content
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '读取文件失败')
    emit('update:visible', false)
  } finally {
    editLoading.value = false
  }
})

async function handleSave() {
  editSaving.value = true
  try {
    await sftpWrite(props.assetId, props.filePath, editContent.value, props.currentKeyId)
    ElMessage.success('保存成功')
    emit('update:visible', false)
    emit('saved')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    editSaving.value = false
  }
}
</script>
