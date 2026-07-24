import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'
import type { IncomingMessage } from 'http'

/**
 * Vite 代理插件：透传真实客户端 IP 到后端（X-Forwarded-For / X-Real-IP）。
 * 解决开发环境下后端只能看到 127.0.0.1 的问题。
 */
function proxyClientIpPlugin() {
  return {
    name: 'proxy-client-ip',
    configureServer(server: any) {
      server.middlewares.use((req: IncomingMessage & { ip?: string }, _res: any, next: () => void) => {
        // Vite 内置的 http-proxy 不会自动加 X-Forwarded-For
        // 这里在请求进入代理之前，手动注入真实客户端 IP
        const clientIp = req.socket?.remoteAddress || ''
        // 去掉 IPv6 前缀 ::ffff:
        const cleanIp = clientIp.replace(/^::ffff:/, '')
        if (cleanIp && cleanIp !== '127.0.0.1' && cleanIp !== '::1') {
          req.headers['x-forwarded-for'] = cleanIp
          req.headers['x-real-ip'] = cleanIp
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
    proxyClientIpPlugin(),
  ],
  optimizeDeps: {
    // Docker 详情页是懒加载路由，预构建其首个独有组件样式，避免首次进入时触发
    // Vite 依赖重新优化并让浏览器中的旧依赖哈希返回 504。
    include: [
      'element-plus/es',
      'element-plus/es/components/base/style/css',
      'element-plus/es/components/progress/style/css',
    ],
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
        // WebSocket 也需要透传 IP（通过 headers）
        headers: {},
        // SSE 流式传输需要禁用代理缓冲
        configure: (proxy: any) => {
          proxy.on('proxyRes', (proxyRes: any) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
    },
  },
})
