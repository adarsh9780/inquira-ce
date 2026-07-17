import { v1Api } from './contracts/v1Api'

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

// Model setup is the first migrated vertical slice. Browser/Tauri development
// keeps using the existing HTTP contract; the Wails executable calls Go directly.
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
    if (this.isNative()) return callWails('GetModelPreferences', String(provider || ''))
    return v1Api.preferences.get(provider)
  },

  updatePreferences(payload) {
    if (this.isNative()) return callWails('UpdateModelPreferences', payload || {})
    return v1Api.preferences.update(payload)
  },

  refreshModels(payload) {
    if (this.isNative()) return callWails('RefreshProviderModels', payload || {})
    return v1Api.preferences.refreshModels(payload)
  },

  searchModels(provider, query, limit = 25) {
    if (this.isNative()) {
      return callWails(
        'SearchProviderModels',
        String(provider || ''),
        String(query || ''),
        Number(limit || 25),
      )
    }
    return v1Api.preferences.searchModels({ provider, query, limit })
  },

  verifyKey(provider, apiKey) {
    if (this.isNative()) {
      return callWails('VerifyProviderAPIKey', String(provider || ''), String(apiKey || ''))
    }
    return v1Api.preferences.verifyKey(provider, apiKey)
  },

  setApiKey(payload) {
    if (this.isNative()) return callWails('SaveProviderConfiguration', payload || {})
    return v1Api.preferences.setApiKey(payload)
  },

  deleteApiKey(provider = 'openrouter') {
    if (this.isNative()) return callWails('DeleteProviderAPIKey', String(provider || 'openrouter'))
    return v1Api.preferences.deleteApiKey(provider)
  },
}

export default modelConnectionService
