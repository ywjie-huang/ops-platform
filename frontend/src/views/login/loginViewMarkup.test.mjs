import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const currentDir = dirname(fileURLToPath(import.meta.url))
const loginView = readFileSync(join(currentDir, 'LoginView.vue'), 'utf8')

test('login page uses the command center visual direction while preserving auth hooks', () => {
  assert.match(loginView, /OPS COMMAND CENTER/)
  assert.match(loginView, /实时运维拓扑/)
  assert.match(loginView, /安全登录/)
  assert.match(loginView, /Auth Gateway/)
  assert.match(loginView, /refreshCaptcha/)
  assert.match(loginView, /handleLogin/)
  assert.match(loginView, /@keyup\.enter="handleLogin"/)
  assert.match(loginView, /captchaUrl/)
})

test('login validation messages are explicit and reserve space before the submit button', () => {
  assert.match(loginView, /message: '用户名不能为空'/)
  assert.match(loginView, /message: '密码不能为空'/)
  assert.match(loginView, /message: '请输入验证码'/)
  assert.match(loginView, /\.login-form :deep\(\.el-form-item__error\) \{[\s\S]*position: static;/)
  assert.match(loginView, /\.login-button \{[\s\S]*margin-top: 8px;/)
})
