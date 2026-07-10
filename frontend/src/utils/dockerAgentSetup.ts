const AGENT_PORT = 9001

function normalizeImage(image: string): string {
  const value = image.trim()
  return /^[A-Za-z0-9._/:@-]+$/.test(value) ? value : ''
}

function normalizeManagementIp(managementIp: string): string {
  const value = managementIp.trim().replace(/^https?:\/\//, '').replace(/\/$/, '')
  return /^[A-Za-z0-9.-]+$/.test(value) ? value : ''
}

function registryHost(image: string): string {
  const firstSegment = image.split('/')[0]
  if (firstSegment.includes('.') || firstSegment.includes(':') || firstSegment === 'localhost') {
    return firstSegment
  }
  return 'docker.io'
}

export function buildAgentEndpoint(managementIp: string): string {
  const ip = normalizeManagementIp(managementIp)
  return ip ? `${ip}:${AGENT_PORT}` : ''
}

export function buildAgentPublishCommand(image: string): string {
  const normalizedImage = normalizeImage(image)
  if (!normalizedImage) return ''

  return [
    'cd agent',
    `docker build -t ${normalizedImage} .`,
    `docker login ${registryHost(normalizedImage)}`,
    `docker push ${normalizedImage}`,
  ].join('\n')
}

export function buildAgentRunCommand(image: string, managementIp: string): string {
  const normalizedImage = normalizeImage(image)
  const ip = normalizeManagementIp(managementIp)
  if (!normalizedImage || !ip) return ''

  return [
    `docker pull ${normalizedImage}`,
    'docker rm -f ops-agent >/dev/null 2>&1 || true',
    'docker run -d \\',
    `  -p ${ip}:${AGENT_PORT}:${AGENT_PORT} \\`,
    '  --name ops-agent \\',
    '  --restart=always \\',
    '  -v /var/run/docker.sock:/var/run/docker.sock \\',
    `  ${normalizedImage}`,
  ].join('\n')
}
