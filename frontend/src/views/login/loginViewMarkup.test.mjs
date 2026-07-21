import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const currentDir = dirname(fileURLToPath(import.meta.url))
const loginView = readFileSync(join(currentDir, 'LoginView.vue'), 'utf8')

test('login page uses spotlight split layout with brand topology panel', () => {
  assert.match(loginView, /Ops Platform/)
  assert.match(loginView, /INTERNAL OPS CONSOLE/)
  assert.match(loginView, /运维拓扑/)
  assert.match(loginView, /示意接入关系 · 非实时状态/)
  assert.match(loginView, /安全登录/)
  assert.match(loginView, /opsctl login --env production/)
  assert.match(loginView, /监控告警/)
  assert.match(loginView, /refreshCaptcha/)
  assert.match(loginView, /handleLogin/)
  assert.match(loginView, /@keyup\.enter="handleLogin"/)
  assert.match(loginView, /captchaUrl/)
  assert.match(loginView, /usernameRef/)
  assert.match(loginView, /safeRedirectPath/)
})

test('login page removes fake operational metrics and pseudo status', () => {
  assert.doesNotMatch(loginView, /0 incidents/)
  assert.doesNotMatch(loginView, /HEALTHY/)
  assert.doesNotMatch(loginView, /SECURITY GATEWAY/)
  assert.doesNotMatch(loginView, /OPS COMMAND CENTER/)
  assert.doesNotMatch(loginView, /在线资产/)
  assert.doesNotMatch(loginView, /活跃告警/)
  assert.doesNotMatch(loginView, /容器实例/)
  assert.doesNotMatch(loginView, /巡检通过率/)
  assert.doesNotMatch(loginView, /事件流/)
  assert.doesNotMatch(loginView, />24ms</)
})

test('login validation messages are explicit and reserve space before the submit button', () => {
  assert.match(loginView, /message: '用户名不能为空'/)
  assert.match(loginView, /message: '密码不能为空'/)
  assert.match(loginView, /message: '请输入验证码'/)
  assert.match(loginView, /\.login-form :deep\(\.el-form-item__error\) \{[\s\S]*position: static;/)
  assert.match(loginView, /\.login-button \{[\s\S]*margin-top: 8px;/)
  assert.match(loginView, /prefers-reduced-motion/)
})
