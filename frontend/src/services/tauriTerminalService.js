import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import { EventsOn } from '../../wailsjs/runtime/runtime'

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function isTauriRuntime() {
  return typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
}

function isNativeRuntime() {
  return Boolean(wailsApp()?.StartTerminalSession) || isTauriRuntime()
}

async function getTauriCore() {
  return { invoke, listen }
}

export const tauriTerminalService = {
  isTauriRuntime,
  isNativeRuntime,

  async startSession({ workspaceId, sessionId, cwd = null, cols = 120, rows = 32, onData = null, onExit = null }) {
    const app = wailsApp()
    if (app?.StartTerminalSession) {
      const disposeData = EventsOn('terminal:pty-data', (body) => {
        if (body?.session_id !== sessionId) return
        if (typeof onData === 'function') onData(String(body?.data || ''))
      }) || (() => {})
      const disposeExit = EventsOn('terminal:pty-exit', (body) => {
        if (body?.session_id !== sessionId) return
        if (typeof onExit === 'function') onExit(body)
      }) || (() => {})
      try {
        const response = await app.StartTerminalSession({
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
    }
    if (!isTauriRuntime()) {
      throw new Error('Interactive terminal is only available in the desktop app.')
    }

    const { invoke, listen } = await getTauriCore()
    const payload = {
      session_id: sessionId,
      sessionId,
      cwd,
      cols,
      rows,
    }

    const [unlistenData, unlistenExit, response] = await Promise.all([
      listen('terminal:pty-data', (event) => {
        const body = event?.payload || {}
        if (body?.session_id !== sessionId) return
        if (typeof onData === 'function') {
          onData(String(body?.data || ''))
        }
      }),
      listen('terminal:pty-exit', (event) => {
        const body = event?.payload || {}
        if (body?.session_id !== sessionId) return
        if (typeof onExit === 'function') onExit(body)
      }),
      invoke('tauri_terminal_start', payload),
    ])

    return {
      ...response,
      async dispose() {
        unlistenData()
        unlistenExit()
      },
    }
  },

  async write(sessionId, data) {
    const app = wailsApp()
    if (app?.WriteTerminalSession) return app.WriteTerminalSession(sessionId, data)
    const { invoke } = await getTauriCore()
    return invoke('tauri_terminal_write', { session_id: sessionId, sessionId, data })
  },

  async resize(sessionId, cols, rows) {
    const app = wailsApp()
    if (app?.ResizeTerminalSession) return app.ResizeTerminalSession(sessionId, cols, rows)
    const { invoke } = await getTauriCore()
    return invoke('tauri_terminal_resize', { session_id: sessionId, sessionId, cols, rows })
  },

  async stop(sessionId) {
    const app = wailsApp()
    if (app?.StopTerminalSession) return app.StopTerminalSession(sessionId)
    const { invoke } = await getTauriCore()
    return invoke('tauri_terminal_stop', { session_id: sessionId, sessionId })
  },
}

export default tauriTerminalService
