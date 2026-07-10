import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const setupModule = await import(
  new URL('../src/utils/dockerAgentSetup.ts', import.meta.url).href
)
const {
  buildAgentEndpoint,
  buildAgentPublishCommand,
  buildAgentRunCommand,
} = setupModule

const image = 'registry.example.com/ops/ops-agent:v1.0.0'

test('generates source build and registry publish commands', () => {
  const command = buildAgentPublishCommand(image)

  assert.match(command, /^cd agent/m)
  assert.match(command, /docker build -t registry\.example\.com\/ops\/ops-agent:v1\.0\.0 \./)
  assert.match(command, /docker login registry\.example\.com/)
  assert.match(command, /docker push registry\.example\.com\/ops\/ops-agent:v1\.0\.0/)
})

test('generates target-host pull and management-network run commands', () => {
  const command = buildAgentRunCommand(image, '10.10.20.15')

  assert.match(command, /docker pull registry\.example\.com\/ops\/ops-agent:v1\.0\.0/)
  assert.match(command, /-p 10\.10\.20\.15:9001:9001/)
  assert.match(command, /-v \/var\/run\/docker\.sock:\/var\/run\/docker\.sock/)
  assert.match(command, /registry\.example\.com\/ops\/ops-agent:v1\.0\.0$/)
})

test('returns empty commands until required values are supplied', () => {
  assert.equal(buildAgentPublishCommand('   '), '')
  assert.equal(buildAgentRunCommand(image, ''), '')
  assert.equal(buildAgentRunCommand('', '10.10.20.15'), '')
  assert.equal(buildAgentPublishCommand('repo/image:latest; rm -rf /'), '')
  assert.equal(buildAgentRunCommand(image, '10.10.20.15;curl attacker'), '')
})

test('builds the platform endpoint from the management address', () => {
  assert.equal(buildAgentEndpoint('10.10.20.15'), '10.10.20.15:9001')
  assert.equal(buildAgentEndpoint(''), '')
})

test('Docker host registration uses a three-step source deployment flow', async () => {
  const source = await readFile(
    new URL('../src/views/containers/DockerView.vue', import.meta.url),
    'utf8',
  )

  assert.match(source, /<el-step title="发布镜像"/)
  assert.match(source, /<el-step title="部署 Agent"/)
  assert.match(source, /<el-step title="注册主机"/)
  assert.match(source, /v-model="agentImage"/)
  assert.match(source, /v-model="agentManagementIp"/)
  assert.match(source, /buildAgentPublishCommand/)
  assert.match(source, /buildAgentRunCommand/)
  assert.match(source, /hostForm\.endpoint = buildAgentEndpoint/)
  assert.doesNotMatch(source, /hub1\.lczy\.com/)
})

test('Agent documentation describes build, push, pull, run, and registration', async () => {
  const readme = await readFile(new URL('../../agent/README.md', import.meta.url), 'utf8')
  const dockerfile = await readFile(new URL('../../agent/Dockerfile', import.meta.url), 'utf8')
  const agentSource = await readFile(new URL('../../agent/docker_agent.py', import.meta.url), 'utf8')

  assert.match(readme, /cd agent/)
  assert.ok(readme.includes('docker build -t <你的镜像仓库>/ops-agent:latest'))
  assert.ok(readme.includes('docker push <你的镜像仓库>/ops-agent:latest'))
  assert.ok(readme.includes('docker pull <你的镜像仓库>/ops-agent:latest'))
  assert.match(readme, /-p 10.10.20.15:9001:9001/)
  assert.match(readme, /服务器启动参数与防火墙/)
  assert.doesNotMatch(readme, /hub1.lczy.com/)
  assert.doesNotMatch(dockerfile, /hub1.lczy.com/)
  assert.doesNotMatch(agentSource, /hub1.lczy.com/)
})
