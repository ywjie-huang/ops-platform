import { createReadStream, existsSync, statSync } from 'node:fs'
import { extname, join, normalize } from 'node:path'
import { createServer } from 'node:http'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('.', import.meta.url))
const preferredPort = Number(process.env.PORT || 3217)
const host = '127.0.0.1'

const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml; charset=utf-8',
}

function resolvePath(urlPath) {
  const rawPath = decodeURIComponent(urlPath.split('?')[0])
  const relativePath = rawPath === '/' ? '/dashboard-duty-preview.html' : rawPath
  const safePath = normalize(relativePath).replace(/^(\.\.[/\\])+/, '')
  return join(root, safePath)
}

function sendFile(res, filePath) {
  const ext = extname(filePath).toLowerCase()
  res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' })
  createReadStream(filePath).pipe(res)
}

function startServer(port) {
  const server = createServer((req, res) => {
    const filePath = resolvePath(req.url || '/')

    if (!existsSync(filePath) || !statSync(filePath).isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('Not Found')
      return
    }

    sendFile(res, filePath)
  })

  server.on('error', (error) => {
    if (error.code === 'EADDRINUSE') {
      startServer(port + 1)
      return
    }
    throw error
  })

  server.listen(port, host, () => {
    const url = `http://${host}:${port}/dashboard-duty-preview.html`
    console.log(url)
  })
}

startServer(preferredPort)
