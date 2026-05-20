<template>
  <div class="ssh-toolbar">
    <div class="toolbar-left">
      <el-button text size="small" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <el-divider direction="vertical" />
      <span class="host-info">
        <span :class="['status-dot', connected ? 'dot-green' : 'dot-grey']" />
        <strong>{{ hostName }}</strong>
        <span class="host-ip">{{ hostIp }}</span>
      </span>
    </div>

    <div class="toolbar-center">
      <el-tooltip content="复制选中内容" placement="bottom">
        <el-button text size="small" @click="$emit('copy')" :disabled="!connected">
          <el-icon><CopyDocument /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="粘贴" placement="bottom">
        <el-button text size="small" @click="$emit('paste')" :disabled="!connected">
          <el-icon><DocumentCopy /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="清屏" placement="bottom">
        <el-button text size="small" @click="$emit('clear')" :disabled="!connected">
          <el-icon><Delete /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="缩小字体" placement="bottom">
        <el-button text size="small" @click="$emit('change-font-size', -1)">
          <span style="font-size:12px;font-weight:700">A-</span>
        </el-button>
      </el-tooltip>
      <span class="font-size-label">{{ fontSize }}px</span>
      <el-tooltip content="放大字体" placement="bottom">
        <el-button text size="small" @click="$emit('change-font-size', 1)">
          <span style="font-size:16px;font-weight:700">A+</span>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="全屏" placement="bottom">
        <el-button text size="small" @click="$emit('toggle-fullscreen')">
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <div class="toolbar-right">
      <el-tooltip content="文件管理器" placement="bottom">
        <el-button
          :type="showFilePanel ? 'primary' : 'default'"
          text size="small"
          @click="$emit('toggle-file-panel')"
          :disabled="!connected"
        >
          <el-icon><FolderOpened /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip v-if="connected" content="断开连接" placement="bottom">
        <el-button text size="small" type="danger" @click="$emit('disconnect')">
          <el-icon><SwitchButton /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip v-else content="重新连接" placement="bottom">
        <el-button text size="small" type="success" @click="$emit('reconnect')">
          <el-icon><RefreshRight /></el-icon>
        </el-button>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ArrowLeft, CopyDocument, DocumentCopy, Delete, FullScreen, FolderOpened,
  SwitchButton, RefreshRight,
} from '@element-plus/icons-vue'

defineProps<{
  hostName: string
  hostIp: string
  connected: boolean
  fontSize: number
  showFilePanel: boolean
}>()

defineEmits<{
  copy: []
  paste: []
  clear: []
  'change-font-size': [delta: number]
  'toggle-fullscreen': []
  'toggle-file-panel': []
  disconnect: []
  reconnect: []
}>()
</script>

<style lang="scss" scoped>
.ssh-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: 0 12px;
  background: #24283b;
  border-bottom: 1px solid #33467c;
  flex-shrink: 0;
  user-select: none;
  .el-button { color: #a9b1d6; &:hover { color: #c0caf5; } }
  .el-divider { border-color: #33467c; }
}
.toolbar-left, .toolbar-center, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}
.host-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #c0caf5;
  .host-ip { color: #565f89; font-size: 12px; }
}
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  &.dot-green { background: #9ece6a; box-shadow: 0 0 6px rgba(158,206,106,0.5); }
  &.dot-grey { background: #565f89; }
}
.font-size-label {
  font-size: 11px;
  color: #565f89;
  min-width: 30px;
  text-align: center;
}
</style>
