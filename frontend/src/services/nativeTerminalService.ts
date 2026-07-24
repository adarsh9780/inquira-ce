import { EventsOn } from '../../wailsjs/runtime/runtime'
import { nativeApp, requireNativeMethod } from '../api/native'
import type { NativeMethod, NativeMethodName, NativeRecord } from '../types/native'

interface StartTerminalOptions {
  workspaceId: unknown
  sessionId: string
  cwd?: string | null
  cols?: number
  rows?: number
  onData?: ((data: string) => void) | null
  onExit?: ((event: NativeRecord) => void) | null
}

function isNativeRuntime() {
  return Boolean(nativeApp()?.StartTerminalSession)
}

function requireWailsMethod<Method extends NativeMethodName>(method: Method): NativeMethod<Method> {
  try {
    return requireNativeMethod(method)
  } catch (_error) {
    throw new Error('Interactive terminal is only available in the installed app.')
  }
}

export const nativeTerminalService = {
  isNativeRuntime,

  async startSession({
    workspaceId,
    sessionId,
    cwd = null,
    cols = 120,
    rows = 32,
    onData = null,
    onExit = null,
  }: StartTerminalOptions) {
    const start = requireWailsMethod('StartTerminalSession')
    const disposeData = EventsOn('terminal:pty-data', (bodyValue: unknown) => {
      const body = bodyValue && typeof bodyValue === 'object'
        ? bodyValue as NativeRecord
        : {}
      if (body.session_id !== sessionId) return
      if (onData) onData(String(body.data || ''))
    }) || (() => {})
    const disposeExit = EventsOn('terminal:pty-exit', (bodyValue: unknown) => {
      const body = bodyValue && typeof bodyValue === 'object'
        ? bodyValue as NativeRecord
        : {}
      if (body.session_id !== sessionId) return
      if (onExit) onExit(body)
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

  async write(sessionId: string, data: string) {
    return requireWailsMethod('WriteTerminalSession')(sessionId, data)
  },

  async resize(sessionId: string, cols: number, rows: number) {
    return requireWailsMethod('ResizeTerminalSession')(sessionId, cols, rows)
  },

  async stop(sessionId: string) {
    return requireWailsMethod('StopTerminalSession')(sessionId)
  },
}

export default nativeTerminalService
