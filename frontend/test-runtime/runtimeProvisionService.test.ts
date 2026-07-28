import { afterEach, describe, expect, it, vi } from 'vitest'

import { runtimeProvisionService } from '../src/services/runtimeProvisionService.ts'

afterEach(() => {
  delete window.go
  delete window.runtime
})

describe('runtimeProvisionService Wails bridge', () => {
  it('reads status and provisions only after explicit configuration', async () => {
    const app = {
      RuntimeStatus: vi.fn().mockResolvedValue({ ready: false }),
      RuntimePlan: vi.fn().mockResolvedValue({ steps: [] }),
      ProvisionRuntime: vi.fn().mockResolvedValue({ pythonExecutable: '/runtime/python' }),
      CancelRuntimeProvisioning: vi.fn().mockResolvedValue(true),
      RepairRuntime: vi.fn().mockResolvedValue({ pythonExecutable: '/runtime/repaired/python' }),
      ResetRuntime: vi.fn().mockResolvedValue(true),
      RollbackRuntime: vi.fn().mockResolvedValue({ pythonExecutable: '/runtime/previous/python' }),
      ExportRuntimeDiagnostics: vi.fn().mockResolvedValue(true),
      ChoosePythonExecutable: vi.fn().mockResolvedValue('/company/python'),
      ChooseCertificateBundle: vi.fn().mockResolvedValue('/company/ca.pem'),
    }
    window.go = { main: { App: app } }
    const config = {
      mode: 'external-python',
      pythonVersion: '3.12',
      pythonExecutable: '/company/python',
      defaultIndex: 'https://packages.company/simple',
      useSystemCertificates: true,
    }
    await runtimeProvisionService.status()
    await runtimeProvisionService.plan(config)
    await runtimeProvisionService.provision(config)
    await runtimeProvisionService.cancel()
    await runtimeProvisionService.repair()
    await runtimeProvisionService.reset()
    await runtimeProvisionService.rollback()
    await runtimeProvisionService.exportDiagnostics()
    await runtimeProvisionService.choosePythonExecutable()
    await runtimeProvisionService.chooseCertificateBundle()
    expect(app.RuntimeStatus).toHaveBeenCalledOnce()
    expect(app.RuntimePlan).toHaveBeenCalledWith(config)
    expect(app.ProvisionRuntime).toHaveBeenCalledWith(config)
    expect(app.CancelRuntimeProvisioning).toHaveBeenCalledOnce()
    expect(app.RepairRuntime).toHaveBeenCalledOnce()
    expect(app.ResetRuntime).toHaveBeenCalledOnce()
    expect(app.RollbackRuntime).toHaveBeenCalledOnce()
    expect(app.ExportRuntimeDiagnostics).toHaveBeenCalledOnce()
    expect(app.ChoosePythonExecutable).toHaveBeenCalledOnce()
    expect(app.ChooseCertificateBundle).toHaveBeenCalledOnce()
  })

  it('forwards runtime progress only while an operation is active', async () => {
    let progressListener: ((payload: unknown) => void) | null = null
    const unsubscribe = vi.fn()
    window.runtime = {
      EventsOnMultiple: vi.fn((_name, callback) => {
        progressListener = callback
        return unsubscribe
      }),
    }
    const app = {
      ProvisionRuntime: vi.fn(async () => {
        progressListener?.({
          operation: 'setup',
          stage: 'install-data-worker',
          message: 'Installing the locked data packages.',
          state: 'running',
          current: 4,
          total: 6,
          percent: 66,
        })
        return { pythonExecutable: '/runtime/python' }
      }),
    }
    window.go = { main: { App: app } }
    const updates: unknown[] = []
    await runtimeProvisionService.provision({ mode: 'managed' }, (progress) => updates.push(progress))

    expect(window.runtime.EventsOnMultiple).toHaveBeenCalledWith(
      'runtime-provision-progress',
      expect.any(Function),
      -1,
    )
    expect(updates).toEqual([
      expect.objectContaining({ operation: 'setup', stage: 'install-data-worker', percent: 66 }),
    ])
    expect(unsubscribe).toHaveBeenCalledOnce()
  })
})
