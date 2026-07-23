import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiService } from '../src/services/apiService'

afterEach(() => {
  delete window.go
})

describe('native workspace AI configuration bridge', () => {
  it('gets and updates configuration through Wails', async () => {
    const config = {
      workspace_id: 'workspace-1',
      defaults: { provider: 'openai', main_model: 'gpt-main', lite_model: 'gpt-lite', coding_model: 'gpt-code' },
      overrides: { provider: null, main_model: null, lite_model: null, coding_model: null, allow_llm_data_samples: false },
      effective: { provider: 'openai', main_model: 'gpt-main', lite_model: 'gpt-lite', coding_model: 'gpt-code' },
      readiness: { ready: false, configuration_reviewed: false },
    }
    const app = {
      GetWorkspaceAIConfig: vi.fn().mockResolvedValue(config),
      UpdateWorkspaceAIConfig: vi.fn().mockResolvedValue({ ...config, readiness: { ready: true, configuration_reviewed: true } }),
    }
    window.go = { main: { App: app } }
    const payload = { main_model_override: 'gpt-4.1', allow_llm_data_samples: true }

    await expect(apiService.v1GetWorkspaceAIConfig('workspace-1')).resolves.toEqual(config)
    await apiService.v1UpdateWorkspaceAIConfig('workspace-1', payload)

    expect(app.GetWorkspaceAIConfig).toHaveBeenCalledWith('workspace-1')
    expect(app.UpdateWorkspaceAIConfig).toHaveBeenCalledWith('workspace-1', payload)
  })
})
