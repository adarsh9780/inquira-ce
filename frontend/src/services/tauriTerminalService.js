function isTauriRuntime() {
  return typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
}

async function getTauriCore() {
  const [{ invoke }, { listen }] = await Promise.all([
    import('@tauri-apps/api/core'),
    import('@tauri-apps/api/event'),
  ])
  return { invoke, listen }
}

export const tauriTerminalService = {
  isTauriRuntime,

  async startSession({ sessionId, cwd = null, cols = 120, rows = 32, onData = null, onExit = null }) {
    if (!isTauriRuntime()) {
      throw new Error('Tauri terminal is only available in desktop runtime.')
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
    const { invoke } = await getTauriCore()
    return invoke('tauri_terminal_write', { session_id: sessionId, sessionId, data })
  },

  async resize(sessionId, cols, rows) {
    const { invoke } = await getTauriCore()
    return invoke('tauri_terminal_resize', { session_id: sessionId, sessionId, cols, rows })
  },

  async stop(sessionId) {
    const { invoke } = await getTauriCore()
    return invoke('tauri_terminal_stop', { session_id: sessionId, sessionId })
  },
}

export default tauriTerminalService
