/**
 * 按需注册 Element Plus 图标
 * 只注册路由 meta.icon 和布局中实际用到的图标，避免全量导入 300+ 图标
 */
import type { App } from 'vue'
import {
  Bell,
  BellFilled,
  Box,
  ChatDotRound,
  Connection,
  Cpu,
  DataAnalysis,
  DataLine,
  Document,
  Download,
  Finished,
  Grid,
  Key,
  List,
  Monitor,
  Notebook,
  Odometer,
  PieChart,
  Platform,
  Promotion,
  Search,
  Setting,
  Tools,
  Upload,
  User,
  Warning,
  Fold,
  Expand,
  ArrowDown,
  ArrowRight,
  ArrowLeft,
  Refresh,
} from '@element-plus/icons-vue'

const icons = {
  Bell, BellFilled, Box, ChatDotRound, Connection, Cpu,
  DataAnalysis, DataLine, Document, Download, Finished, Grid,
  Key, List, Monitor, Notebook, Odometer, PieChart, Platform,
  Promotion, Search, Setting, Tools, Upload, User, Warning,
  // 布局组件
  Fold, Expand, ArrowDown, ArrowRight, ArrowLeft, Refresh,
}

export function registerIcons(app: App) {
  for (const [key, component] of Object.entries(icons)) {
    app.component(key, component)
  }
}
