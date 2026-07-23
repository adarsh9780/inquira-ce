function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function callWails(method, ...args) {
  const app = wailsApp()
  if (!app || typeof app[method] !== 'function') {
    throw new Error(`Wails model bridge method is unavailable: ${method}`)
  }
  return app[method](...args)
}

export const modelConnectionService = {
  isNative() {
    return !!wailsApp()
  },

  getOnboardingStatus() {
    if (this.isNative()) return callWails('GetModelOnboardingStatus')
    return Promise.resolve({ completed: true, connection_ready: false, provider: 'openrouter' })
  },

  completeOnboarding() {
    if (this.isNative()) return callWails('CompleteModelOnboarding')
    return Promise.resolve({ completed: true, connection_ready: false, provider: 'openrouter' })
  },

  getPreferences(provider = null) {
    return callWails('GetModelPreferences', String(provider || ''))
  },

  updatePreferences(payload) {
    return callWails('UpdateModelPreferences', payload || {})
  },

  refreshModels(payload) {
    return callWails('RefreshProviderModels', payload || {})
  },

  searchModels(provider, query, limit = 25) {
    return callWails(
      'SearchProviderModels',
      String(provider || ''),
      String(query || ''),
      Number(limit || 25),
    )
  },

  verifyKey(provider, apiKey) {
    return callWails('VerifyProviderAPIKey', String(provider || ''), String(apiKey || ''))
  },

  setApiKey(payload) {
    return callWails('SaveProviderConfiguration', payload || {})
  },

  deleteApiKey(provider = 'openrouter') {
    return callWails('DeleteProviderAPIKey', String(provider || 'openrouter'))
  },
}

export default modelConnectionService
