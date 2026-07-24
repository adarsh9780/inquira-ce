import { invokeNative, nativeApp } from '../api/native'
import type {
  NativeArguments,
  NativeMethodName,
  NativeRecord,
  NativeResult,
} from '../types/native'

function callWails<Method extends NativeMethodName>(
  method: Method,
  ...arguments_: NativeArguments<Method>
): Promise<NativeResult<Method>> {
  return invokeNative(method, ...arguments_)
}

export const modelConnectionService = {
  isNative() {
    return Boolean(nativeApp())
  },

  getOnboardingStatus() {
    if (this.isNative()) return callWails('GetModelOnboardingStatus')
    return Promise.resolve({ completed: true, connection_ready: false, provider: 'openrouter' })
  },

  completeOnboarding() {
    if (this.isNative()) return callWails('CompleteModelOnboarding')
    return Promise.resolve({ completed: true, connection_ready: false, provider: 'openrouter' })
  },

  getPreferences(provider: unknown = null) {
    return callWails('GetModelPreferences', String(provider || ''))
  },

  updatePreferences(payload: NativeRecord) {
    return callWails('UpdateModelPreferences', payload || {})
  },

  refreshModels(payload: NativeRecord) {
    return callWails('RefreshProviderModels', payload || {})
  },

  searchModels(provider: unknown, query: unknown, limit: unknown = 25) {
    return callWails(
      'SearchProviderModels',
      String(provider || ''),
      String(query || ''),
      Number(limit || 25),
    )
  },

  verifyKey(provider: unknown, apiKey: unknown) {
    return callWails('VerifyProviderAPIKey', String(provider || ''), String(apiKey || ''))
  },

  setApiKey(payload: NativeRecord) {
    return callWails('SaveProviderConfiguration', payload || {})
  },

  deleteApiKey(provider: unknown = 'openrouter') {
    return callWails('DeleteProviderAPIKey', String(provider || 'openrouter'))
  },
}

export default modelConnectionService
