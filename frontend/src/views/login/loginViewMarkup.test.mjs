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
