function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function callWails(method, ...args) {
  const app = wailsApp()
  if (!app || typeof app[method] !== 'function') {
    throw new Error(`Wails workspace bridge method is unavailable: ${method}`)
  }
  return app[method](...args)
}

export const workspaceService = {
  isNative() {
    return !!wailsApp()
  },

  list() {
    if (!this.isNative()) return Promise.resolve([])
    return callWails('ListWorkspaces')
  },

  create(name, schemaContext = '') {
    return callWails('CreateWorkspace', {
      name: String(name || ''),
      schema_context: String(schemaContext || ''),
    })
  },

  activate(workspaceId) {
    return callWails('ActivateWorkspace', String(workspaceId || ''))
  },

  update(workspaceId, name, schemaContext = undefined) {
    const request = {
      workspace_id: String(workspaceId || ''),
      name: String(name || ''),
    }
    if (schemaContext !== undefined) request.schema_context = String(schemaContext || '')
    return callWails('UpdateWorkspace', request)
  },

  summary(workspaceId) {
    return callWails('GetWorkspaceSummary', String(workspaceId || ''))
  },

  delete(workspaceId) {
    return callWails('DeleteWorkspace', String(workspaceId || ''))
  },
}

export default workspaceService
