<template>
  <div class="ssh-toolbar">
    <div class="toolbar-left">
      <el-button text size="small" aria-label="返回" @click="$router.back()">
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
        <el-button text size="small" :disabled="!connected" @click="$emit('copy')">
          <el-icon><CopyDocument /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="粘贴" placement="bottom">
        <el-button text size="small" :disabled="!connected" @click="$emit('paste')">
          <el-icon><DocumentCopy /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="清屏" placement="bottom">
        <el-button text size="small" :disabled="!connected" @click="$emit('clear')">
          <el-icon><Delete /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="缩小字体" placement="bottom">
        <el-button text size="small" @click="$emit('change-font-size', -1)">
          <span class="font-button font-button-small">A-</span>
        </el-button>
      </el-tooltip>
      <span class="font-size-label">{{ fontSize }}px</span>
      <el-tooltip content="放大字体" placement="bottom">
        <el-button text size="small" @click="$emit('change-font-size', 1)">
          <span class="font-button font-button-large">A+</span>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="全屏" placement="bottom">
        <el-button text size="small" @click="$emit('toggle-fullscreen')">
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="左右分屏" placement="bottom">
        <el-button text size="small" :disabled="!canSplit" @click="$emit('split-vertical')">
          <el-icon><DCaret /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="上下分屏" placement="bottom">
        <el-button text size="small" :disabled="!canSplit" @click="$emit('split-horizontal')">
          <el-icon class="rotate-icon"><DCaret /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <div class="toolbar-right">
      <el-tooltip content="协作面板" placement="bottom">
        <el-button
          text
          size="small"
          :type="showFilePanel ? 'primary' : 'default'"
          @click="$emit('toggle-file-panel')"
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
  ArrowLeft,
  CopyDocument,
  DCaret,
  Delete,
  DocumentCopy,
  FolderOpened,
  FullScreen,
  RefreshRight,
  SwitchButton,
} from '@element-plus/icons-vue'

defineProps<{
  hostName: string
  hostIp: string
  connected: boolean
  fontSize: number
  showFilePanel: boolean
  canSplit: boolean
}>()

defineEmits<{
  copy: []
  paste: []
  clear: []
  'change-font-size': [delta: number]
  'toggle-fullscreen': []
  'split-vertical': []
  'split-horizontal': []
  'toggle-file-panel': []
  disconnect: []
  reconnect: []
}>()
</script>

<style lang="scss" scoped>
.ssh-toolbar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: 44px;
  padding: 0 10px 0 12px;
  user-select: none;
  background: #171c2c;
  border: 1px solid #303a5c;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgb(0 0 0 / 16%);

  .el-button {
    width: 28px;
    height: 28px;
    color: #aeb8d8;
    border-radius: 6px;

    &:hover {
      color: #f4f7ff;
      background: #242c43;
    }

    &:focus-visible {
      outline: 2px solid #6ea8fe;
      outline-offset: 1px;
    }
  }

  .el-divider {
    height: 18px;
    border-color: #303a5c;
  }
}

.toolbar-left,
.toolbar-center,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.toolbar-center {
  flex: 1 1 auto;
  justify-content: center;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.toolbar-left,
.toolbar-right {
  flex: 0 0 auto;
}

.host-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: #e8edff;
  font-size: 13px;

  strong {
    overflow: hidden;
    max-width: 130px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.host-ip {
  padding: 2px 7px;
  color: #94a1c4;
  background: #101624;
  border: 1px solid #293352;
  border-radius: 999px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.dot-green {
    background: #4ade80;
    box-shadow: 0 0 0 3px rgb(74 222 128 / 14%);
  }

  &.dot-grey {
    background: #65708f;
  }
}

.font-size-label {
  min-width: 38px;
  padding: 2px 6px;
  color: #93a0c0;
  background: #101624;
  border: 1px solid #293352;
  border-radius: 5px;
  font-size: 11px;
  text-align: center;
}

.font-button {
  font-weight: 700;
}

.font-button-small {
  font-size: 12px;
}

.font-button-large {
  font-size: 16px;
}

.rotate-icon {
  transform: rotate(90deg);
}

@media (max-width: 900px) {
  .ssh-toolbar {
    height: 42px;
    min-height: 42px;
    padding: 0 8px;
  }

  .toolbar-center {
    justify-content: flex-start;
  }

  .host-ip {
    display: none;
  }

  .host-info strong {
    max-width: 96px;
  }
}

@media (max-width: 640px) {
  .host-info strong {
    display: none;
  }
}
</style>
