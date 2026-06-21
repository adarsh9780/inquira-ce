

let tauriWsBaseOverride = ''

function toWsBase(rawApiBase) {
  const trimmed = String(rawApiBase || '').trim().replace(/\/+$/, '')
  if (!trimmed) return ''
  if (trimmed.startsWith('ws://') || trimmed.startsWith('wss://')) return trimmed
  if (trimmed.startsWith('https://')) return `wss://${trimmed.slice('https://'.length)}`
  if (trimmed.startsWith('http://')) return `ws://${trimmed.slice('http://'.length)}`
  return ''
}

function initializeTauriWsBase() {
  if (typeof window === 'undefined') return
  if (!window.__TAURI_INTERNALS__) return

  const globalBase = toWsBase(window.__INQUIRA_API_BASE__)
  if (globalBase) {
    tauriWsBaseOverride = globalBase
    return
  }

  import('@tauri-apps/api/core')
    .then(({ invoke }) => invoke('get_backend_url'))
    .then((value) => {
      const resolved = toWsBase(value)
      if (resolved) tauriWsBaseOverride = resolved
    })
    .catch(() => {})
}

function getDefaultWsBase() {
  if (typeof window === 'undefined') {
    return 'ws://127.0.0.1:8000'
  }

  if (window.__TAURI_INTERNALS__) {
    if (tauriWsBaseOverride) return tauriWsBaseOverride
    return 'ws://127.0.0.1:8000'
  }

  const isSecure = window.location.protocol === 'https:'
  const scheme = isSecure ? 'wss:' : 'ws:'

  if (import.meta.env.DEV) {
    const resolvedHost = window.location.hostname === 'localhost' ? '127.0.0.1' : (window.location.hostname || '127.0.0.1')
    const host = `${resolvedHost}:8000`
    return `${scheme}//${host}`
  }

  return `${scheme}//${window.location.host}`
}

function resolveWsBase() {
  const envValue = (import.meta.env.VITE_WS_BASE || '').trim()
  if (envValue) {
    return envValue
  }

  return getDefaultWsBase()
}

initializeTauriWsBase()

function buildWsUrl(path) {
  const base = resolveWsBase().replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}`
}

class SettingsWebSocket {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.progressListeners = new Set()
    this.errorListeners = new Set()
    this.completeListeners = new Set()
    this.workspaceRuntimeStatusListeners = new Set()
    // Support multiple subscribers for connection state
    this.connectionListeners = new Set()

    // Persistent connection properties
    this.isPersistentMode = false
    this.userId = null
    this.reconnectTimer = null
    this.reconnectInterval = 5000 // 5 seconds
    this.lastConnectionAttempt = null
    this.workspaceRuntimeStatusWorkspaceId = ''
    this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = ''
  }

  connect(userId) {
    if (this.socket && this.isConnected) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const wsPath = `/ws/settings/${userId}`
      const wsUrl = buildWsUrl(wsPath)
      this.socket = new WebSocket(wsUrl)
      this.connectionAcknowledged = false

      this.socket.onopen = () => {
        this.isConnected = true
        this.notifyConnectionListeners(true)
        this.sendWorkspaceRuntimeStatusSubscription()
      }

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)

          // Check for connection acknowledgment
          if (data.type === 'connected') {
            this.isConnected = true
            this.connectionAcknowledged = true
            this.notifyConnectionListeners(true)
            this.sendWorkspaceRuntimeStatusSubscription()
            resolve()
          }
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error, 'Raw data:', event.data)
        }
      }

      this.socket.onclose = (event) => {
        this.isConnected = false
        this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = ''
        this.notifyConnectionListeners(false)
        this.handleReconnect()
      }

      this.socket.onerror = (error) => {
        console.error('❌ Settings WebSocket error:', error)
        this.isConnected = false
        this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = ''
        this.notifyConnectionListeners(false)
        reject(error)
      }

      // Timeout for connection acknowledgment - increased to 10 seconds
      setTimeout(() => {
        if (!this.connectionAcknowledged) {
          console.warn('⚠️ WebSocket connection acknowledgment timeout - but WebSocket is open')
          // Don't reject here - WebSocket might still be usable
          // Just resolve since the connection is established
          resolve()
        }
      }, 10000)
    })
  }

  // Persistent connection management
  connectPersistent(userId) {
    if (this.isPersistentMode) {
      console.debug('Persistent connection already active')
      return Promise.resolve()
    }

    console.debug('Starting persistent WebSocket connection for user:', userId)
    this.isPersistentMode = true
    this.userId = userId

    return this.attemptConnection()
  }

  disconnectPersistent() {
    console.debug('Stopping persistent WebSocket connection')
    this.isPersistentMode = false
    this.userId = null
    this.stopReconnectTimer()
    this.disconnect()
  }

  attemptConnection() {
    if (!this.isPersistentMode || !this.userId) {
      return Promise.reject(new Error('Persistent mode not active'))
    }

    this.lastConnectionAttempt = Date.now()

    return this.connect(this.userId)
      .then(() => {
        console.debug('✅ Persistent connection established')
        this.stopReconnectTimer()
      })
      .catch((error) => {
        console.error('❌ Persistent connection failed:', error)
        this.scheduleReconnect()
        throw error
      })
  }

  scheduleReconnect() {
    if (!this.isPersistentMode) return

    this.stopReconnectTimer()

    console.debug(`Scheduling reconnection in ${this.reconnectInterval / 1000} seconds...`)

    this.reconnectTimer = setTimeout(() => {
      if (this.isPersistentMode) {
        console.debug('🔄 Attempting to reconnect...')
        this.attemptConnection().catch(() => {
          // Error already logged in attemptConnection
        })
      }
    }, this.reconnectInterval)
  }

  stopReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  handleMessage(data) {
    console.debug('WebSocket message received:', data)

    switch (data.type) {
      case 'connected':
        console.debug('WebSocket connection confirmed')
        break

      case 'progress':
        this.progressListeners.forEach((listener) => {
          try {
            listener({
              type: 'progress',
              message: data.message,
              fact: data.fact,
              stage: data.stage,
              progress: data.progress,
            })
          } catch (_error) {
            // Keep processing other listeners.
          }
        })
        break

      case 'completed':
        this.completeListeners.forEach((listener) => {
          try {
            listener(data.result)
          } catch (_error) {
            // Keep processing other listeners.
          }
        })
        break

      case 'error':
        this.errorListeners.forEach((listener) => {
          try {
            listener(data.message || data.error)
          } catch (_error) {
            // Keep processing other listeners.
          }
        })
        break

      case 'workspace_runtime_status':
        this.workspaceRuntimeStatusListeners.forEach((listener) => {
          try {
            listener({
              workspaceId: String(data.workspace_id || '').trim(),
              status: String(data.status || 'missing').trim().toLowerCase() || 'missing',
            })
          } catch (_error) {
            // Keep processing other listeners.
          }
        })
        break

      default:
        console.debug('Unknown message type:', data.type)
    }
  }

  handleReconnect() {
    if (!this.isPersistentMode) return
    console.debug('Connection lost, scheduling persistent reconnection...')
    this.scheduleReconnect()
  }

  send(message) {
    if (this.socket && this.isConnected) {
      this.socket.send(JSON.stringify(message))
    } else {
      console.error('WebSocket not connected')
    }
  }

  setWorkspaceRuntimeStatusWorkspace(workspaceId) {
    this.workspaceRuntimeStatusWorkspaceId = String(workspaceId || '').trim()
    if (!this.workspaceRuntimeStatusWorkspaceId) {
      this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = ''
      return
    }
    this.sendWorkspaceRuntimeStatusSubscription()
  }

  sendWorkspaceRuntimeStatusSubscription() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return
    const workspaceId = String(this.workspaceRuntimeStatusWorkspaceId || '').trim()
    if (!workspaceId) return
    if (workspaceId === this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId) return
    this.socket.send(JSON.stringify({
      type: 'subscribe_workspace_runtime_status',
      workspace_id: workspaceId,
    }))
    this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = workspaceId
  }

  subscribeProgress(callback) {
    if (typeof callback !== 'function') return () => { }
    this.progressListeners.add(callback)
    return () => {
      this.progressListeners.delete(callback)
    }
  }

  subscribeComplete(callback) {
    if (typeof callback !== 'function') return () => { }
    this.completeListeners.add(callback)
    return () => {
      this.completeListeners.delete(callback)
    }
  }

  subscribeError(callback) {
    if (typeof callback !== 'function') return () => { }
    this.errorListeners.add(callback)
    return () => {
      this.errorListeners.delete(callback)
    }
  }

  subscribeWorkspaceRuntimeStatus(callback) {
    if (typeof callback !== 'function') return () => { }
    this.workspaceRuntimeStatusListeners.add(callback)
    return () => {
      this.workspaceRuntimeStatusListeners.delete(callback)
    }
  }

  onConnection(callback) {
    if (typeof callback !== 'function') return () => { }
    this.connectionListeners.add(callback)
    // Immediately notify current connection state
    callback(this.isConnected)
    // Return unsubscribe function
    return () => {
      this.connectionListeners.delete(callback)
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
      this.isConnected = false
      this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = ''
      this.notifyConnectionListeners(false)
    }

    // If in persistent mode, schedule reconnection
    if (this.isPersistentMode) {
      this.scheduleReconnect()
    }
  }

  // Notify all listeners of connection state changes
  notifyConnectionListeners(connected) {
    try {
      this.connectionListeners.forEach((cb) => {
        try { cb(connected) } catch (err) { console.error('Connection listener error:', err) }
      })
    } catch (e) {
      // Ensure one bad listener doesn't break others
      console.error('Error notifying connection listeners:', e)
    }
  }

  // Get connection status information
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      isPersistentMode: this.isPersistentMode,
      lastConnectionAttempt: this.lastConnectionAttempt,
      timeSinceLastAttempt: this.lastConnectionAttempt ? Date.now() - this.lastConnectionAttempt : null
    }
  }
}

// Export singleton instance
export const settingsWebSocket = new SettingsWebSocket()
export default settingsWebSocket
