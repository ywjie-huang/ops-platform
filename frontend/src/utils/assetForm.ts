export type AssetAuthMethod = 'password' | 'key'

export type AssetForm = {
  name: string
  asset_type: string
  ip_address: string
  status: string
  owner: string
  description: string
  spec: string
  os: string
  ssh_port: number
  ssh_username: string
  ssh_password: string
  auth_method: AssetAuthMethod
  ssh_key_id: number | null
}

export type AssetFormSource = {
  name?: string | null
  asset_type?: string | null
  ip_address?: string | null
  status?: string | null
  owner?: string | null
  description?: string | null
  spec?: string | null
  os?: string | null
  ssh_username?: string | null
  ssh_port?: number | null
  ssh_key_id?: number | null
}

export function createAssetForm(): AssetForm {
  return {
    name: '',
    asset_type: '云主机',
    ip_address: '',
    status: '使用中',
    owner: '',
    description: '',
    spec: '',
    os: '',
    ssh_port: 22,
    ssh_username: 'root',
    ssh_password: '',
    auth_method: 'password',
    ssh_key_id: null,
  }
}

export function createAssetFormFromAsset(asset: AssetFormSource): AssetForm {
  return {
    ...createAssetForm(),
    name: asset.name || '',
    asset_type: asset.asset_type || '云主机',
    ip_address: asset.ip_address || '',
    status: asset.status || '使用中',
    owner: asset.owner || '',
    description: asset.description || '',
    spec: asset.spec || '',
    os: asset.os || '',
    ssh_port: Number(asset.ssh_port || 22),
    ssh_username: asset.ssh_username || 'root',
    auth_method: asset.ssh_key_id ? 'key' : 'password',
    ssh_key_id: asset.ssh_key_id || null,
  }
}

export function isValidIpAddress(value: string) {
  const parts = value.trim().split('.')
  if (parts.length !== 4) return false
  return parts.every((part) => {
    if (!/^\d+$/.test(part)) return false
    const octet = Number(part)
    return octet >= 0 && octet <= 255 && String(octet) === part
  })
}

export function buildAssetPayload(form: AssetForm) {
  const payload = {
    name: form.name,
    asset_type: form.asset_type,
    ip_address: form.ip_address.trim(),
    status: form.status,
    owner: form.owner.trim(),
    description: form.description,
    spec: form.spec,
    os: form.os,
    ssh_port: Number(form.ssh_port || 22),
    ssh_username: form.ssh_username.trim(),
    ssh_password: form.ssh_password,
    ssh_key_id: form.ssh_key_id,
  }

  if (form.auth_method === 'password') {
    payload.ssh_key_id = null
  } else {
    payload.ssh_password = ''
  }

  return payload
}
