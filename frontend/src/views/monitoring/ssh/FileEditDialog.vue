<template>
  <el-dialog
    :model-value="visible"
    :title="`编辑: ${filePath}`"
    width="80%"
    top="5vh"
    destroy-on-close
    @update:model-value="$emit('update:visible', $event)"
  >
    <div v-loading="editLoading">
      <el-input
        v-model="editContent"
        class="file-editor"
        type="textarea"
        :rows="28"
        :autosize="false"
      />
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

<style scoped lang="scss">
.file-editor {
  :deep(.el-textarea__inner) {
    min-height: 62vh !important;
    color: #d7def7;
    background: #0f1420;
    border-color: #27304d;
    border-radius: 6px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.65;
  }
}
</style>
