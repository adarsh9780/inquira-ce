import { afterEach, describe, expect, it, vi } from 'vitest'

import { runtimeProvisionService } from '../src/services/runtimeProvisionService'

afterEach(() => {
  delete window.go
})

describe('runtimeProvisionService Wails bridge', () => {
  it('reads status and provisions only after explicit configuration', async () => {
    const app = {
      RuntimeStatus: vi.fn().mockResolvedValue({ ready: false }),
      ProvisionRuntime: vi.fn().mockResolvedValue({ pythonExecutable: '/runtime/python' }),
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
    await runtimeProvisionService.provision(config)
    expect(app.RuntimeStatus).toHaveBeenCalledOnce()
    expect(app.ProvisionRuntime).toHaveBeenCalledWith(config)
  })
})
