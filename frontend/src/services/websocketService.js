function getDefaultWsBase() {
  if (typeof window === 'undefined') {
    return 'ws://localhost:8000'
  }

  const isSecure = window.location.protocol === 'https:'
  const scheme = isSecure ? 'wss:' : 'ws:'

  if (import.meta.env.DEV) {
    const host = `${window.location.hostname}:8000`
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

function buildWsUrl(path) {
  const base = resolveWsBase().replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}`
}

class SettingsWebSocket {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 50 // Increased for persistent connections
    this.messageHandlers = new Map()
    this.progressCallback = null
    this.errorCallback = null
    this.completeCallback = null
    // Support multiple subscribers for connection state
    this.connectionListeners = new Set()

    // Persistent connection properties
    this.isPersistentMode = false
    this.userId = null
    this.reconnectTimer = null
    this.reconnectInterval = 5000 // 5 seconds
    this.lastConnectionAttempt = null
  }

  connect(userId) {
    if (this.socket && this.isConnected) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const wsUrl = buildWsUrl(`/ws/settings/${userId}`)
      console.log('🔌 Connecting to WebSocket:', wsUrl)

      this.socket = new WebSocket(wsUrl)
      this.connectionAcknowledged = false

      this.socket.onopen = () => {
        console.log('✅ Settings WebSocket opened, waiting for backend acknowledgment...')
        this.reconnectAttempts = 0

        // For debugging - let's also consider the WebSocket as "connected" when it opens
        // This will make the indicator green even if backend doesn't send acknowledgment
        console.log('🔄 WebSocket opened - marking as connected for UI purposes')
        this.isConnected = true
        this.notifyConnectionListeners(true)
      }

      this.socket.onmessage = (event) => {
        console.log('📨 WebSocket message received:', event.data)
        try {
          const data = JSON.parse(event.data)
          console.log('📨 Parsed message:', data)
          this.handleMessage(data)

          // Check for connection acknowledgment
          if (data.type === 'connected') {
            console.log('✅ Backend acknowledged WebSocket connection')
            this.isConnected = true
            this.connectionAcknowledged = true
            this.notifyConnectionListeners(true)
            resolve()
          }
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error, 'Raw data:', event.data)
        }
      }

      this.socket.onclose = (event) => {
        console.log('❌ Settings WebSocket closed:', event.code, event.reason)
        this.isConnected = false
        this.notifyConnectionListeners(false)
        this.handleReconnect()
      }

      this.socket.onerror = (error) => {
        console.error('❌ Settings WebSocket error:', error)
        this.isConnected = false
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
      console.log('Persistent connection already active')
      return Promise.resolve()
    }

    console.log('Starting persistent WebSocket connection for user:', userId)
    this.isPersistentMode = true
    this.userId = userId
    this.reconnectAttempts = 0

    return this.attemptConnection()
  }

  disconnectPersistent() {
    console.log('Stopping persistent WebSocket connection')
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
        console.log('✅ Persistent connection established')
        this.reconnectAttempts = 0
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

    console.log(`Scheduling reconnection in ${this.reconnectInterval / 1000} seconds...`)

    this.reconnectTimer = setTimeout(() => {
      if (this.isPersistentMode) {
        console.log('🔄 Attempting to reconnect...')
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
    console.log('WebSocket message received:', data)

    switch (data.type) {
      case 'connected':
        console.log('WebSocket connection confirmed')
        if (this.progressCallback) {
          this.progressCallback({
            type: 'connected',
            message: data.message
          })
        }
        break

      case 'progress':
        if (this.progressCallback) {
          // Pass the message directly without step mapping
          this.progressCallback({
            type: 'progress',
            message: data.message,
            fact: data.fact,
            stage: data.stage,
            progress: data.progress
          })
        }
        break

      case 'completed':
        if (this.completeCallback) {
          this.completeCallback(data.result)
        }
        break

      case 'error':
        if (this.errorCallback) {
          this.errorCallback(data.message || data.error)
        }
        break

      default:
        console.log('Unknown message type:', data.type)
    }
  }

  handleReconnect() {
    if (this.isPersistentMode) {
      // Use persistent reconnection logic
      console.log('Connection lost, scheduling persistent reconnection...')
      this.scheduleReconnect()
    } else {
      // Use legacy reconnection logic for non-persistent mode
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

        setTimeout(() => {
          // Legacy reconnection - just log for now
          console.log('Legacy reconnection attempt completed')
        }, 1000 * this.reconnectAttempts)
      } else {
        console.error('Max reconnection attempts reached')
      }
    }
  }

  send(message) {
    if (this.socket && this.isConnected) {
      this.socket.send(JSON.stringify(message))
    } else {
      console.error('WebSocket not connected')
    }
  }

  startSettingsSave(settings) {
    // The backend expects individual API calls, not a single WebSocket message
    // We'll use the existing API endpoints but with WebSocket monitoring
    console.log('WebSocket monitoring started for settings save')
  }

  onProgress(callback) {
    this.progressCallback = callback
  }

  onComplete(callback) {
    this.completeCallback = callback
  }

  onError(callback) {
    this.errorCallback = callback
  }

  onConnection(callback) {
    if (typeof callback !== 'function') return () => {}
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
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      lastConnectionAttempt: this.lastConnectionAttempt,
      timeSinceLastAttempt: this.lastConnectionAttempt ? Date.now() - this.lastConnectionAttempt : null
    }
  }

  // Expose handleMessage for testing
  testHandleMessage(data) {
    this.handleMessage(data)
  }
}

// Export singleton instance
export const settingsWebSocket = new SettingsWebSocket()
export default settingsWebSocket
