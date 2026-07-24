import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePreferencesStore } from '../src/stores/preferencesStore'

describe('preferencesStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('normalizes provider preferences without retaining credentials', () => {
    const store = usePreferencesStore()
    store.applyPreferencesResponse({
      provider: 'openai',
      main_model: 'gpt-main',
      models: ['gpt-main', 'gpt-lite'],
      api_key_configured: true,
    })
    expect(store.llmProvider).toBe('openai')
    expect(store.selectedModel).toBe('gpt-main')
    expect(store.selectedProviderApiKeyPresent).toBe(true)
    expect(store.apiKey).toBe('')
  })
})
