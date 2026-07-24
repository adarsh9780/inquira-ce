import { invokeNative } from './native.ts'

type RecordValue = Record<string, unknown>

export const preferencesApi = {
  get(provider: unknown = null) {
    return invokeNative('GetModelPreferences', String(provider || ''))
  },
  update(payload: RecordValue = {}) {
    return invokeNative('UpdateModelPreferences', payload)
  },
  searchModels(provider: unknown, query: unknown, limit = 25) {
    return invokeNative(
      'SearchProviderModels',
      String(provider || ''),
      String(query || ''),
      Number(limit || 25),
    )
  },
  terms() {
    return invokeNative('GetTermsAndConditions')
  },
}
