import { afterEach, describe, expect, it, vi } from 'vitest'

import { runtimeProvisionService } from '../src/services/runtimeProvisionService'

afterEach(() => {
  delete window.go
})

describe('runtimeProvisionService Wails bridge', () => {
  it('reads status and provisions only after explicit configuration', async () => {
    const app = {
      RuntimeStatus: vi.fn().mockResolvedValue({ ready: false }),
      RuntimePlan: vi.fn().mockResolvedValue({ steps: [] }),
      ProvisionRuntime: vi.fn().mockResolvedValue({ pythonExecutable: '/runtime/python' }),
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
    await runtimeProvisionService.choosePythonExecutable()
    await runtimeProvisionService.chooseCertificateBundle()
    expect(app.RuntimeStatus).toHaveBeenCalledOnce()
    expect(app.RuntimePlan).toHaveBeenCalledWith(config)
    expect(app.ProvisionRuntime).toHaveBeenCalledWith(config)
    expect(app.ChoosePythonExecutable).toHaveBeenCalledOnce()
    expect(app.ChooseCertificateBundle).toHaveBeenCalledOnce()
  })
})
