function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

export const catalogService = {
  isNative() {
    return !!wailsApp()
  },

  prepare(workspaceId) {
    const app = wailsApp()
    if (!app || typeof app.PrepareWorkspaceCatalog !== 'function') {
      return Promise.reject(new Error('The workspace analysis catalog is available in the Wails application.'))
    }
    return app.PrepareWorkspaceCatalog(String(workspaceId || ''))
  },
}

export default catalogService
