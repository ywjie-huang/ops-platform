import { createRouter, createWebHistory } from 'vue-router'
import routes from './modules/routes'
import { getToken } from '@/utils/auth'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// 白名单路由
const whiteList = ['/login']

router.beforeEach(async (to, _from, next) => {
  NProgress.start()
  document.title = `${to.meta.title || ''} - 运维管理平台`

  const token = getToken()

  if (token) {
    if (to.path === '/login') {
      next({ path: '/' })
    } else {
      // 检查是否已获取用户信息
      const { useAuthStore } = await import('@/stores/modules/auth')
      const authStore = useAuthStore()
      if (authStore.userInfo) {
        next()
      } else {
        try {
          await authStore.fetchUserInfo()
          next({ ...to, replace: true })
        } catch {
          await authStore.logout()
          next(`/login?redirect=${to.path}`)
        }
      }
    }
  } else {
    if (whiteList.includes(to.path)) {
      next()
    } else {
      next(`/login?redirect=${to.path}`)
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
