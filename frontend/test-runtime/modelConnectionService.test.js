import { afterEach, describe, expect, it, vi } from 'vitest'

import { modelConnectionService } from '../src/services/modelConnectionService'

afterEach(() => {
  delete window.go
})

describe('modelConnectionService Wails bridge', () => {
  it('routes model setup operations directly to Go in the Wails runtime', async () => {
    const app = {
      GetModelPreferences: vi.fn().mockResolvedValue({ llm_provider: 'openai' }),
      UpdateModelPreferences: vi.fn().mockResolvedValue({ selected_model: 'gpt-4.1' }),
      RefreshProviderModels: vi.fn().mockResolvedValue({ detail: 'refreshed' }),
      SearchProviderModels: vi.fn().mockResolvedValue({ models: [] }),
      VerifyProviderAPIKey: vi.fn().mockResolvedValue({ valid: true, error: '' }),
      SaveProviderConfiguration: vi.fn().mockResolvedValue({ api_key_present: true }),
      DeleteProviderAPIKey: vi.fn().mockResolvedValue({ message: 'deleted' }),
    }
    window.go = { main: { App: app } }

    await modelConnectionService.getPreferences('openai')
    await modelConnectionService.updatePreferences({ selected_model: 'gpt-4.1' })
    await modelConnectionService.refreshModels({ provider: 'openai' })
    await modelConnectionService.searchModels('openai', 'gpt', 10)
    await modelConnectionService.verifyKey('openai', 'secret')
    await modelConnectionService.setApiKey({ provider: 'openai', api_key: 'secret' })
    await modelConnectionService.deleteApiKey('openai')

    expect(app.GetModelPreferences).toHaveBeenCalledWith('openai')
    expect(app.UpdateModelPreferences).toHaveBeenCalledWith({ selected_model: 'gpt-4.1' })
    expect(app.RefreshProviderModels).toHaveBeenCalledWith({ provider: 'openai' })
    expect(app.SearchProviderModels).toHaveBeenCalledWith('openai', 'gpt', 10)
    expect(app.VerifyProviderAPIKey).toHaveBeenCalledWith('openai', 'secret')
    expect(app.SaveProviderConfiguration).toHaveBeenCalledWith({ provider: 'openai', api_key: 'secret' })
    expect(app.DeleteProviderAPIKey).toHaveBeenCalledWith('openai')
  })
})
