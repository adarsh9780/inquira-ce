import { nativeApp } from '../api/native'
import type { NativeRecord } from '../types/native'

const DEFAULT_SCOPE = 'default'

export const localStateService = {
  async loadSnapshot(scope = DEFAULT_SCOPE): Promise<NativeRecord | null> {
    const app = nativeApp()
    if (app?.LoadLocalState) {
      try {
        return await app.LoadLocalState(scope)
      } catch (error) {
        console.warn('Failed to load local state snapshot through Wails:', error)
        return null
      }
    }
    return null
  },

  async saveSnapshot(snapshot: NativeRecord, scope = DEFAULT_SCOPE): Promise<boolean> {
    const app = nativeApp()
    if (app?.SaveLocalState) {
      try {
        return Boolean(await app.SaveLocalState(scope, snapshot))
      } catch (error) {
        console.warn('Failed to save local state snapshot through Wails:', error)
        return false
      }
    }
    return false
  }
}

export default localStateService
