function toWsBase(apiBase) {
  const normalized = String(apiBase || '/api').replace(/\/$/, '')

  if (normalized.startsWith('http://')) {
    return `ws://${normalized.slice('http://'.length)}`
  }
  if (normalized.startsWith('https://')) {
    return `wss://${normalized.slice('https://'.length)}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${normalized}`
}

export function createNotificationSocket({ token, onState, onOpen, onError, onClose }) {
  if (!token) return null

  const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'
  const wsBase = toWsBase(apiBase)
  const url = `${wsBase}/auth/me/notifications/ws?token=${encodeURIComponent(token)}`

  const socket = new WebSocket(url)

  socket.onopen = () => {
    if (typeof onOpen === 'function') onOpen()
  }

  socket.onmessage = (event) => {
    if (!event?.data) return
    try {
      const payload = JSON.parse(event.data)
      if (payload?.type === 'notification_state' && typeof onState === 'function') {
        onState(payload)
      }
    } catch {
      // ignore malformed websocket payload
    }
  }

  socket.onerror = (event) => {
    if (typeof onError === 'function') onError(event)
  }

  socket.onclose = (event) => {
    if (typeof onClose === 'function') onClose(event)
  }

  return socket
}
