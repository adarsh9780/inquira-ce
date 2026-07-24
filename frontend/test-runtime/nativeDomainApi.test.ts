import { afterEach, describe, expect, it, vi } from 'vitest'
import { artifactApi } from '../src/api/artifacts'
import { invokeNative, requireNativeMethod } from '../src/api/native'
import { workspaceApi } from '../src/api/workspaces'

describe('typed Wails API transport', () => {
  afterEach(() => {
    delete window.go
    artifactApi.clearRowsCache()
  })

  it('reports a clear desktop-only error when a bridge method is unavailable', () => {
    expect(() => requireNativeMethod('MissingMethod')).toThrow(
      'The MissingMethod desktop bridge is unavailable',
    )
  })

  it('invokes native methods with their original arguments', async () => {
    const method = vi.fn(async () => ({ ok: true }))
    window.go = { main: { App: { Example: method } } }
    await expect(invokeNative('Example', 'value')).resolves.toEqual({ ok: true })
    expect(method).toHaveBeenCalledWith('value')
  })

  it('normalizes workspace runtime readiness', async () => {
    window.go = {
      main: {
        App: {
          RuntimeStatus: vi.fn(async () => ({ ready: true })),
          GetWorkspaceKernelStatus: vi.fn(async () => ({ status: 'busy' })),
        },
      },
    }
    await expect(workspaceApi.runtimeStatus('workspace-a')).resolves.toEqual({ status: 'busy' })
  })

  it('deduplicates identical artifact row requests', async () => {
    const rows = vi.fn(async () => ({ rows: [{ value: 1 }] }))
    window.go = { main: { App: { GetWorkspaceArtifactRows: rows } } }
    await Promise.all([
      artifactApi.workspaceRows('workspace-a', 'artifact-a', 0, 50),
      artifactApi.workspaceRows('workspace-a', 'artifact-a', 0, 50),
    ])
    expect(rows).toHaveBeenCalledTimes(1)
  })
})
