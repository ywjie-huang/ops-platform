<template>
  <div class="file-panel">
    <div class="file-panel-header">
      <h4>文件管理</h4>
    </div>

    <div class="file-path-bar">
      <el-input
        v-model="currentPath"
        size="small"
        :prefix-icon="Folder"
        @keyup.enter="navigateTo(currentPath)"
      />
      <el-button size="small" text aria-label="刷新当前目录" @click="navigateTo(currentPath)">
        <el-icon><RefreshRight /></el-icon>
      </el-button>
    </div>

    <div class="file-shortcuts">
      <el-button size="small" text @click="navigateTo('/')">/</el-button>
      <el-button size="small" text @click="navigateTo('/root')">~</el-button>
      <el-button size="small" text @click="navigateTo('/tmp')">/tmp</el-button>
      <el-button size="small" text @click="navigateTo('/etc')">/etc</el-button>
      <el-button size="small" text @click="navigateTo('/var/log')">/var/log</el-button>
    </div>

    <div class="file-actions">
      <el-upload :show-file-list="false" :before-upload="handleUpload" accept="*">
        <el-button size="small" type="primary" :loading="uploading">
          <el-icon><Upload /></el-icon>
          上传
        </el-button>
      </el-upload>
      <el-button size="small" @click="handleMkdir">
        <el-icon><FolderAdd /></el-icon>
        新建目录
      </el-button>
      <el-button size="small" aria-label="刷新文件列表" @click="navigateTo(currentPath)">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <div class="file-list" v-loading="fileLoading">
      <div
        v-if="currentPath !== '/'"
        class="file-item"
        role="button"
        tabindex="0"
        @click="navigateTo(parentPath)"
        @dblclick="navigateTo(parentPath)"
        @keyup.enter="navigateTo(parentPath)"
      >
        <el-icon class="file-icon"><FolderOpened /></el-icon>
        <span class="file-name">..</span>
        <span class="file-meta">上级目录</span>
      </div>

      <div
        v-for="item in fileList"
        :key="item.path"
        class="file-item"
        :class="{ 'is-dir': item.is_dir, 'is-editing': editingPath === item.path }"
        :role="editingPath === item.path ? undefined : 'button'"
        :tabindex="editingPath === item.path ? -1 : 0"
        @click="selectedFile = item"
        @dblclick="handleDoubleClick(item)"
        @keyup.enter="handleDoubleClick(item)"
      >
        <el-icon class="file-icon" :class="item.is_dir ? 'dir-icon' : 'file-icon-type'">
          <FolderOpened v-if="item.is_dir" />
          <Document v-else />
        </el-icon>

        <template v-if="editingPath === item.path">
          <el-input
            ref="editInputRef"
            v-model="editingName"
            size="small"
            class="rename-input"
            @click.stop
            @dblclick.stop
            @keydown.stop
            @keyup.enter.stop="confirmRename(item)"
            @keyup.escape.stop="editingPath = ''"
            @blur="confirmRename(item)"
          />
        </template>
        <template v-else>
          <span class="file-name" :title="item.name">{{ item.name }}</span>
        </template>

        <span class="file-meta">{{ item.is_dir ? '' : formatSize(item.size) }}</span>
        <span class="file-date">{{ item.modified?.slice(5, 16) }}</span>

        <el-dropdown
          trigger="click"
          class="file-menu"
          @click.stop
          @command="(cmd: string) => handleFileAction(cmd, item)"
        >
          <button
            type="button"
            class="file-menu-button"
            :aria-label="`打开 ${item.name} 的文件操作菜单`"
            @click.stop
            @keydown.stop
          >
            <el-icon class="file-menu-icon"><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="!item.is_dir" command="download">
                <el-icon><Download /></el-icon>
                下载
              </el-dropdown-item>
              <el-dropdown-item v-if="!item.is_dir && isTextFile(item.name)" command="edit">
                <el-icon><Edit /></el-icon>
                编辑
              </el-dropdown-item>
              <el-dropdown-item command="rename">
                <el-icon><EditPen /></el-icon>
                重命名
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided>
                <el-icon><Delete /></el-icon>
                <span class="danger-text">删除</span>
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
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete,
  Document,
  Download,
  Edit,
  EditPen,
  Folder,
  FolderAdd,
  FolderOpened,
  MoreFilled,
  Refresh,
  RefreshRight,
  Upload,
} from '@element-plus/icons-vue'
import { sftpDownload, sftpList, sftpMkdir, sftpRemove, sftpRename, sftpUpload } from '@/api/sftp'

const props = defineProps<{
  connected: boolean
  assetId: number
  currentKeyId: number | undefined
}>()

const emit = defineEmits<{
  'edit-file': [path: string]
  'path-change': [path: string]
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
  return parts.length > 1 ? `/${parts.slice(0, -1).join('/')}` : '/'
})

watch(() => props.connected, (connected) => {
  if (connected) {
    navigateTo(currentPath.value)
  } else {
    fileList.value = []
  }
})

async function navigateTo(path: string) {
  if (!props.connected) return

  fileLoading.value = true
  try {
    const res: any = await sftpList(props.assetId, path, props.currentKeyId)
    currentPath.value = res.data.path
    fileList.value = res.data.items
    emit('path-change', currentPath.value)
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
    case 'download':
      downloadFile(item)
      break
    case 'edit':
      emit('edit-file', item.path)
      break
    case 'rename':
      startRename(item)
      break
    case 'delete':
      deleteFile(item)
      break
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
    ElMessage.success('开始下载')
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
      `确认删除${item.is_dir ? '目录' : '文件'}「${item.name}」？${item.is_dir ? '目录必须为空才能删除。' : ''}`,
      '确认删除',
      { type: 'warning' },
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
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #151b2b;
}

.file-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #27304d;

  h4 {
    margin: 0;
    color: #e8edff;
    font-size: 13px;
  }
}

.file-path-bar {
  display: flex;
  gap: 6px;
  padding: 9px 12px 7px;

  :deep(.el-input__wrapper) {
    background: #101624;
    border: 1px solid #293352;
    border-radius: 6px;
    box-shadow: none;
  }

  :deep(.el-input__inner) {
    color: #e8edff;
  }
}

.file-shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 12px 8px;

  .el-button {
    color: #8cb9ff;
    font-size: 12px;
  }
}

.file-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid #202843;
  border-bottom: 1px solid #27304d;

  :deep(.el-button) {
    border-radius: 6px;
  }
}

.file-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 0;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    background: #344164;
    border-radius: 3px;
  }
}

.file-item {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 36px;
  padding: 6px 12px;
  color: #aeb8d8;
  cursor: pointer;
  font-size: 13px;
  border-left: 2px solid transparent;
  transition: background 0.15s ease-out, border-color 0.15s ease-out;

  &:hover {
    background: #1d2539;
    border-left-color: #6ea8fe;
  }

  &:focus-visible {
    outline: 2px solid #7aa2f7;
    outline-offset: -2px;
  }

  &.is-dir .file-name {
    color: #8cb9ff;
  }
}

.file-icon {
  flex-shrink: 0;
  font-size: 16px;
}

.dir-icon {
  color: #8cb9ff;
}

.file-icon-type {
  color: #7f8aaa;
}

.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  min-width: 50px;
  color: #7f8aaa;
  font-size: 11px;
  text-align: right;
}

.file-date {
  min-width: 70px;
  color: #5e6a8d;
  font-size: 11px;
}

.file-menu {
  margin-left: auto;
}

.file-menu-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  color: #7f8aaa;
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;

  &:hover,
  &:focus-visible {
    background: #2a314b;
    color: #f4f7ff;
    outline: none;
  }
}

.file-menu-icon {
  color: currentcolor;
}

.rename-input {
  flex: 1;

  :deep(.el-input__wrapper) {
    background: #101624;
    border: 1px solid #6ea8fe;
    box-shadow: none;
  }

  :deep(.el-input__inner) {
    color: #e8edff;
  }
}

.empty-files {
  padding: 20px;

  :deep(.el-empty__description p) {
    color: #7f8aaa;
  }
}

.danger-text {
  color: var(--danger-color);
}

@media (prefers-reduced-motion: reduce) {
  .file-item {
    transition: none;
  }
}

@media (max-width: 900px) {
  .file-panel-header {
    display: none;
  }

  .file-path-bar {
    padding: 8px 10px 5px;
  }

  .file-shortcuts {
    padding: 0 10px 6px;
  }

  .file-actions {
    padding: 6px 10px;
  }

  .file-list {
    padding: 2px 0;
  }

  .file-item {
    min-height: 32px;
    padding: 4px 10px;
  }
}
</style>
