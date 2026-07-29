type AssetSshLike = {
  ssh_username?: string | null
  ssh_port?: number | null
  ssh_key_id?: number | null
  has_ssh_password?: boolean
}

type SshKeyLike = {
  id: number
  username?: string | null
  port?: number | null
  is_default?: boolean
}

export type LoginFormState = {
  username: string
  port: number
  authMode: string
}

export type ConnectFormData = {
  username: string
  password: string
  port: number
  authMode: string
}

export function getInitialLoginState(asset: AssetSshLike, sshKeys: SshKeyLike[]): LoginFormState {
  const assetUsername = asset.ssh_username || 'root'
  const assetPort = asset.ssh_port || 22

  if (asset.ssh_key_id) {
    const boundKey = sshKeys.find((key) => key.id === asset.ssh_key_id)
    return {
      authMode: `key-${asset.ssh_key_id}`,
      username: boundKey?.username || assetUsername,
      port: boundKey?.port || assetPort,
    }
  }

  if (asset.has_ssh_password) {
    return {
      authMode: 'asset',
      username: assetUsername,
      port: assetPort,
    }
  }

  const defaultKey = sshKeys.find((key) => key.is_default)
  if (defaultKey) {
    return {
      authMode: `key-${defaultKey.id}`,
      username: defaultKey.username || assetUsername,
      port: defaultKey.port || assetPort,
    }
  }

  return {
    authMode: 'asset',
    username: assetUsername,
    port: assetPort,
  }
}

export function buildAuthPayload(formData: ConnectFormData) {
  const authData: Record<string, string | number> = {
    username: formData.username,
    port: formData.port,
  }

  if (formData.authMode === 'asset') {
    if (formData.password) authData.password = formData.password
    return authData
  }

  const keyId = Number(formData.authMode.replace('key-', ''))
  authData.key_id = keyId
  return authData
}

export function buildWebSocketAuthPayload(
  formData: ConnectFormData,
  token: string,
): Record<string, string | number> & { token: string } {
  return {
    ...buildAuthPayload(formData),
    token,
  }
}
