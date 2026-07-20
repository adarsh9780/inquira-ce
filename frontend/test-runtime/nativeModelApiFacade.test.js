import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiService } from '../src/services/apiService'

afterEach(() => {
  delete window.go
})

describe('native model API facade', () => {
  it('routes every model operation used outside onboarding through Wails', async () => {
    const app = {
      GetModelPreferences: vi.fn().mockResolvedValue({ llm_provider: 'openai' }),
      UpdateModelPreferences: vi.fn().mockResolvedValue({ selected_model: 'gpt-main' }),
      RefreshProviderModels: vi.fn().mockResolvedValue({ available_models: ['gpt-main'] }),
      SearchProviderModels: vi.fn().mockResolvedValue({ models: ['gpt-main'] }),
      VerifyProviderAPIKey: vi.fn().mockResolvedValue({ valid: true }),
      SaveProviderConfiguration: vi.fn().mockResolvedValue({ api_key_present: true }),
      DeleteProviderAPIKey: vi.fn().mockResolvedValue({ message: 'deleted' }),
    }
    window.go = { main: { App: app } }

    const update = { selected_model: 'gpt-main' }
    const refresh = { provider: 'openai' }
    const configuration = { provider: 'openai', api_key: 'secret' }

    await apiService.v1GetPreferences('openai')
    await apiService.v1UpdatePreferences(update)
    await apiService.v1RefreshProviderModels(refresh)
    await apiService.v1SearchProviderModels('openai', 'gpt', 12)
    await apiService.v1VerifyApiKey('openai', 'secret')
    await apiService.v1SetApiKey(configuration)
    await apiService.v1DeleteApiKey('openai')

    expect(app.GetModelPreferences).toHaveBeenCalledWith('openai')
    expect(app.UpdateModelPreferences).toHaveBeenCalledWith(update)
    expect(app.RefreshProviderModels).toHaveBeenCalledWith(refresh)
    expect(app.SearchProviderModels).toHaveBeenCalledWith('openai', 'gpt', 12)
    expect(app.VerifyProviderAPIKey).toHaveBeenCalledWith('openai', 'secret')
    expect(app.SaveProviderConfiguration).toHaveBeenCalledWith(configuration)
    expect(app.DeleteProviderAPIKey).toHaveBeenCalledWith('openai')
  })

  it('normalizes the legacy key arguments before crossing the Wails boundary', async () => {
    const app = { SaveProviderConfiguration: vi.fn().mockResolvedValue({ api_key_present: true }) }
    window.go = { main: { App: app } }

    await apiService.v1SetApiKey('secret', 'anthropic')

    expect(app.SaveProviderConfiguration).toHaveBeenCalledWith({
      api_key: 'secret',
      provider: 'anthropic',
    })
  })
})
