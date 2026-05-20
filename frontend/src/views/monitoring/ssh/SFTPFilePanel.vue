<template>
  <transition name="slide-right">
    <div v-if="visible" class="file-panel">
      <div class="file-panel-header">
        <h4>📁 文件管理</h4>
        <el-button text size="small" @click="$emit('update:visible', false); $emit('refit-terminal')">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <!-- 路径导航 -->
      <div class="file-path-bar">
        <el-input v-model="currentPath" size="small" @keyup.enter="navigateTo(currentPath)" :prefix-icon="Folder" />
        <el-button size="small" text @click="navigateTo(currentPath)">
          <el-icon><RefreshRight /></el-icon>
        </el-button>
      </div>

      <!-- 快捷路径 -->
      <div class="file-shortcuts">
        <el-button size="small" text @click="navigateTo('/')">/</el-button>
        <el-button size="small" text @click="navigateTo('/root')">~</el-button>
        <el-button size="small" text @click="navigateTo('/tmp')">/tmp</el-button>
        <el-button size="small" text @click="navigateTo('/etc')">/etc</el-button>
        <el-button size="small" text @click="navigateTo('/var/log')">/var/log</el-button>
      </div>

      <!-- 操作按钮 -->
      <div class="file-actions">
        <el-upload :show-file-list="false" :before-upload="handleUpload" accept="*">
          <el-button size="small" type="primary" :loading="uploading">
            <el-icon><Upload /></el-icon> 上传
          </el-button>
        </el-upload>
        <el-button size="small" @click="handleMkdir">
          <el-icon><FolderAdd /></el-icon> 新建目录
        </el-button>
        <el-button size="small" @click="navigateTo(currentPath)">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>

      <!-- 文件列表 -->
      <div class="file-list" v-loading="fileLoading">
        <div v-if="currentPath !== '/'" class="file-item" @click="navigateTo(parentPath)" @dblclick="navigateTo(parentPath)">
          <el-icon class="file-icon"><FolderOpened /></el-icon>
          <span class="file-name">..</span>
          <span class="file-meta">上级目录</span>
        </div>

        <div v-for="item in fileList" :key="item.path" class="file-item"
          :class="{ 'is-dir': item.is_dir, 'is-editing': editingPath === item.path }"
          @click="selectedFile = item" @dblclick="handleDoubleClick(item)">
          <el-icon class="file-icon" :class="item.is_dir ? 'dir-icon' : 'file-icon-type'">
            <FolderOpened v-if="item.is_dir" />
            <Document v-else />
          </el-icon>

          <template v-if="editingPath === item.path">
            <el-input v-model="editingName" size="small" @keyup.enter="confirmRename(item)"
              @keyup.escape="editingPath = ''" @blur="confirmRename(item)" ref="editInputRef" class="rename-input" />
          </template>
          <template v-else>
            <span class="file-name" :title="item.name">{{ item.name }}</span>
          </template>

          <span class="file-meta">{{ item.is_dir ? '' : formatSize(item.size) }}</span>
          <span class="file-date">{{ item.modified?.slice(5, 16) }}</span>

          <el-dropdown trigger="click" @command="(cmd: string) => handleFileAction(cmd, item)" class="file-menu">
            <el-icon class="file-menu-icon"><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="!item.is_dir" command="download">
                  <el-icon><Download /></el-icon> 下载
                </el-dropdown-item>
                <el-dropdown-item v-if="!item.is_dir && isTextFile(item.name)" command="edit">
                  <el-icon><Edit /></el-icon> 编辑
                </el-dropdown-item>
                <el-dropdown-item command="rename">
                  <el-icon><EditPen /></el-icon> 重命名
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon><Delete /></el-icon>
                  <span style="color:var(--el-color-danger)">删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div v-if="!fileLoading && fileList.length === 0 && currentPath !== '/'" class="empty-files">
          <el-empty description="空目录" :image-size="60" />
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Close, RefreshRight, Upload, FolderAdd, Refresh, Folder,
  Document, MoreFilled, Download, Edit, EditPen, Delete, FolderOpened,
} from '@element-plus/icons-vue'
import { sftpList, sftpUpload, sftpDownload, sftpMkdir, sftpRemove, sftpRename } from '@/api/sftp'

const props = defineProps<{
  visible: boolean
  connected: boolean
  assetId: number
  currentKeyId: number | undefined
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  'edit-file': [path: string]
  'refit-terminal': []
}>()

const currentPath = ref('/')
const fileList = ref<any[]>([])
const fileLoading = ref(false)
const uploading = ref(false)
const selectedFile = ref<any>(null)
const editingPath = ref('')
const editingName = ref('')
const editInputRef = ref<any>(null)

const parentPath = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  return parts.length > 1 ? '/' + parts.slice(0, -1).join('/') : '/'
})

watch(() => props.visible, (val) => {
  if (val && props.connected) navigateTo(currentPath.value)
})

async function navigateTo(path: string) {
  if (!props.connected) return
  fileLoading.value = true
  try {
    const res: any = await sftpList(props.assetId, path, props.currentKeyId)
    currentPath.value = res.data.path
    fileList.value = res.data.items
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    fileLoading.value = false
  }
}

function handleDoubleClick(item: any) {
  if (item.is_dir) {
    navigateTo(item.path)
  } else if (isTextFile(item.name)) {
    emit('edit-file', item.path)
  }
}

function handleFileAction(cmd: string, item: any) {
  switch (cmd) {
    case 'download': downloadFile(item); break
    case 'edit': emit('edit-file', item.path); break
    case 'rename': startRename(item); break
    case 'delete': deleteFile(item); break
  }
}

function isTextFile(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return ['txt', 'log', 'conf', 'cfg', 'yml', 'yaml', 'json', 'xml', 'sh', 'bash', 'py', 'js', 'ts',
    'java', 'go', 'rs', 'c', 'cpp', 'h', 'hpp', 'md', 'sql', 'ini', 'toml', 'env', 'properties',
    'html', 'css', 'scss', 'less', 'vue', 'jsx', 'tsx', 'dockerfile', 'nginx', 'service'].includes(ext)
    || !name.includes('.')
}

function formatSize(bytes: number) {
  if (bytes === 0) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}M`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)}G`
}

async function handleUpload(file: File) {
  if (!props.connected) return false
  uploading.value = true
  try {
    await sftpUpload(props.assetId, currentPath.value, file, props.currentKeyId)
    ElMessage.success(`上传成功: ${file.name}`)
    navigateTo(currentPath.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
  return false
}

async function downloadFile(item: any) {
  try {
    await sftpDownload(props.assetId, item.path, props.currentKeyId)
    ElMessage.success('下载开始')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '下载失败')
  }
}

async function handleMkdir() {
  try {
    const { value } = await ElMessageBox.prompt('请输入目录名称', '新建目录', {
      inputPattern: /^[^\s]+$/,
      inputErrorMessage: '目录名不能为空',
    })
    const newPath = `${currentPath.value.replace(/\/$/, '')}/${value}`
    await sftpMkdir(props.assetId, newPath, props.currentKeyId)
    ElMessage.success('创建成功')
    navigateTo(currentPath.value)
  } catch {}
}

async function deleteFile(item: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${item.is_dir ? '目录' : '文件'}「${item.name}」？${item.is_dir ? '目录必须为空才能删除。' : ''}`,
      '确认删除', { type: 'warning' }
    )
    await sftpRemove(props.assetId, item.path, item.is_dir, props.currentKeyId)
    ElMessage.success('删除成功')
    navigateTo(currentPath.value)
  } catch {}
}

function startRename(item: any) {
  editingPath.value = item.path
  editingName.value = item.name
  nextTick(() => editInputRef.value?.focus())
}

async function confirmRename(item: any) {
  if (!editingName.value || editingName.value === item.name) {
    editingPath.value = ''
    return
  }
  const dir = item.path.substring(0, item.path.lastIndexOf('/'))
  const newPath = `${dir}/${editingName.value}`
  try {
    await sftpRename(props.assetId, item.path, newPath, props.currentKeyId)
    editingPath.value = ''
    navigateTo(currentPath.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重命名失败')
  }
}

defineExpose({ navigateTo, currentPath })
</script>

<style lang="scss" scoped>
.file-panel {
  width: 360px;
  background: #1f2335;
  border-left: 1px solid #33467c;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.file-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #33467c;
  h4 { margin: 0; font-size: 13px; color: #c0caf5; }
  .el-button { color: #a9b1d6; }
}
.file-path-bar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  :deep(.el-input__wrapper) { background: #24283b; border-color: #33467c; box-shadow: none; }
  :deep(.el-input__inner) { color: #c0caf5; }
}
.file-shortcuts {
  display: flex;
  gap: 2px;
  padding: 0 12px 8px;
  flex-wrap: wrap;
  .el-button { color: #7aa2f7; font-size: 12px; }
}
.file-actions {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid #33467c;
}
.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: #33467c; border-radius: 3px; }
}
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  transition: background 0.12s;
  font-size: 13px;
  color: #a9b1d6;
  &:hover { background: #24283b; }
  &.is-dir .file-name { color: #7aa2f7; }
}
.file-icon { font-size: 16px; flex-shrink: 0; }
.dir-icon { color: #7aa2f7; }
.file-icon-type { color: #565f89; }
.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-meta {
  font-size: 11px;
  color: #565f89;
  min-width: 50px;
  text-align: right;
}
.file-date {
  font-size: 11px;
  color: #414868;
  min-width: 70px;
}
.file-menu { margin-left: auto; }
.file-menu-icon {
  color: #565f89;
  cursor: pointer;
  &:hover { color: #c0caf5; }
}
.rename-input {
  flex: 1;
  :deep(.el-input__wrapper) { background: #24283b; border-color: #7aa2f7; box-shadow: none; }
  :deep(.el-input__inner) { color: #c0caf5; }
}
.empty-files {
  padding: 20px;
  :deep(.el-empty__description p) { color: #565f89; }
}
.slide-right-enter-active, .slide-right-leave-active {
  transition: width 0.25s ease;
}
.slide-right-enter-from, .slide-right-leave-to {
  width: 0 !important;
  overflow: hidden;
}
</style>
