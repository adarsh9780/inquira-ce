import { EventsOn } from '../../wailsjs/runtime/runtime'

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function isNativeRuntime() {
  return Boolean(wailsApp()?.StartTerminalSession)
}

function requireWailsMethod(method) {
  const app = wailsApp()
  if (!app || typeof app[method] !== 'function') {
    throw new Error('Interactive terminal is only available in the installed app.')
  }
  return app[method].bind(app)
}

export const nativeTerminalService = {
  isNativeRuntime,

  async startSession({ workspaceId, sessionId, cwd = null, cols = 120, rows = 32, onData = null, onExit = null }) {
    const app = wailsApp()
    const start = requireWailsMethod('StartTerminalSession')
    const disposeData = EventsOn('terminal:pty-data', (body) => {
      if (body?.session_id !== sessionId) return
      if (typeof onData === 'function') onData(String(body?.data || ''))
    }) || (() => {})
    const disposeExit = EventsOn('terminal:pty-exit', (body) => {
      if (body?.session_id !== sessionId) return
      if (typeof onExit === 'function') onExit(body)
    }) || (() => {})
    try {
      const response = await start({
        workspace_id: String(workspaceId || ''),
        session_id: sessionId,
        cwd,
        cols,
        rows,
      })
      return {
        ...response,
        async dispose() {
          disposeData()
          disposeExit()
        },
      }
    } catch (error) {
      disposeData()
      disposeExit()
      throw error
    }
  },

  async write(sessionId, data) {
    return requireWailsMethod('WriteTerminalSession')(sessionId, data)
  },

  async resize(sessionId, cols, rows) {
    return requireWailsMethod('ResizeTerminalSession')(sessionId, cols, rows)
  },

  async stop(sessionId) {
    return requireWailsMethod('StopTerminalSession')(sessionId)
  },
}

export default nativeTerminalService
