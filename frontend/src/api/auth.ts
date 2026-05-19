import request from './request'

export function login(data: { username: string; password: string; captcha_id: string; captcha_code: string }) {
  return request.post('/auth/login', data)
}

export async function getCaptcha(): Promise<{ captchaId: string; imageUrl: string }> {
  const resp: any = await request.get('/auth/captcha', { responseType: 'blob' })
  const captchaId = resp.headers?.['x-captcha-id'] || ''
  const blob = resp.data instanceof Blob ? resp.data : new Blob([resp.data])
  const imageUrl = URL.createObjectURL(blob)
  return { captchaId, imageUrl }
}

export function getMe() {
  return request.get('/auth/me')
}

export function logout() {
  return request.post('/auth/logout')
}
