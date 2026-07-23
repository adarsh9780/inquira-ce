const DEFAULT_SCOPE = 'default'

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

export const localStateService = {
  async loadSnapshot(scope = DEFAULT_SCOPE) {
    const app = wailsApp()
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

  async saveSnapshot(snapshot, scope = DEFAULT_SCOPE) {
    const app = wailsApp()
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
