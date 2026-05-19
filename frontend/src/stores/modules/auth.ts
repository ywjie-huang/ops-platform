import { defineStore } from 'pinia'
import { login as loginApi, getMe, logout as logoutApi } from '@/api/auth'
import { setToken, getToken, removeToken } from '@/utils/auth'

interface UserInfo {
  id: number
  username: string
  full_name: string
  roles: string[]
  permissions: Record<string, boolean>
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken() || '',
    userInfo: null as UserInfo | null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.username || '',
    fullName: (state) => state.userInfo?.full_name || '',
    permissions: (state) => state.userInfo?.permissions || {},
  },
  actions: {
    async login(username: string, password: string, captchaId: string, captchaCode: string) {
      const res: any = await loginApi({ username, password, captcha_id: captchaId, captcha_code: captchaCode })
      const token = res.data.access_token
      this.token = token
      setToken(token)
      return res
    },
    async fetchUserInfo() {
      const res: any = await getMe()
      this.userInfo = res.data
      return res.data
    },
    async logout() {
      try { await logoutApi() } catch {}
      this.token = ''
      this.userInfo = null
      removeToken()
    },
    hasPermission(code: string): boolean {
      return !!this.permissions[code]
    },
  },
})
