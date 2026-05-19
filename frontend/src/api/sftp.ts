import request from './request'
import axios from 'axios'
import { getToken } from '@/utils/auth'

/** 列出目录内容 */
export function sftpList(assetId: number, path: string, keyId?: number) {
  return request.get(`/ssh/${assetId}/sftp/list`, {
    params: { path, key_id: keyId },
  })
}

/** 读取文件内容 */
export function sftpRead(assetId: number, path: string, keyId?: number) {
  return request.get(`/ssh/${assetId}/sftp/read`, {
    params: { path, key_id: keyId },
  })
}

/** 写入文件内容 */
export function sftpWrite(assetId: number, path: string, content: string, keyId?: number) {
  const form = new FormData()
  form.append('content', content)
  if (keyId) form.append('key_id', String(keyId))
  return request.post(`/ssh/${assetId}/sftp/write?path=${encodeURIComponent(path)}`, form)
}

/** 上传文件 */
export function sftpUpload(assetId: number, dirPath: string, file: File, keyId?: number) {
  const form = new FormData()
  form.append('path', dirPath)
  form.append('file', file)
  if (keyId) form.append('key_id', String(keyId))
  return request.post(`/ssh/${assetId}/sftp/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 下载文件（流式 blob） */
export async function sftpDownload(assetId: number, path: string, keyId?: number) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const token = getToken()
  let url = `${baseURL}/ssh/${assetId}/sftp/download?path=${encodeURIComponent(path)}`
  if (keyId) url += `&key_id=${keyId}`

  const res = await axios.get(url, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  // 从 Content-Disposition 提取文件名
  const disposition = res.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : path.split('/').pop() || 'download'

  // 触发浏览器下载
  const blob = new Blob([res.data])
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  a.click()
  URL.revokeObjectURL(blobUrl)
}

/** 创建目录 */
export function sftpMkdir(assetId: number, path: string, keyId?: number) {
  return request.post(`/ssh/${assetId}/sftp/mkdir?path=${encodeURIComponent(path)}`, null, {
    params: { key_id: keyId },
  })
}

/** 删除文件/目录 */
export function sftpRemove(assetId: number, path: string, isDir: boolean, keyId?: number) {
  return request.post(`/ssh/${assetId}/sftp/remove`, null, {
    params: { path, is_dir: isDir, key_id: keyId },
  })
}

/** 重命名 */
export function sftpRename(assetId: number, oldPath: string, newPath: string, keyId?: number) {
  return request.post(`/ssh/${assetId}/sftp/rename`, null, {
    params: { old_path: oldPath, new_path: newPath, key_id: keyId },
  })
}
