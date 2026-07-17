import { apiService } from './apiService'

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

// Keep the copied browser/Tauri UI usable against the Python API while the
// Wails executable moves workspace metadata to Go.
export const workspaceService = {
  isNative() {
    return !!wailsApp()
  },

  list() {
    if (this.isNative()) return callWails('ListWorkspaces')
    return apiService.v1ListWorkspaces()
  },

  create(name, schemaContext = '') {
    if (this.isNative()) {
      return callWails('CreateWorkspace', {
        name: String(name || ''),
        schema_context: String(schemaContext || ''),
      })
    }
    return apiService.v1CreateWorkspace(name, schemaContext)
  },

  activate(workspaceId) {
    if (this.isNative()) return callWails('ActivateWorkspace', String(workspaceId || ''))
    return apiService.v1ActivateWorkspace(workspaceId)
  },

  update(workspaceId, name, schemaContext = undefined) {
    if (this.isNative()) {
      const request = {
        workspace_id: String(workspaceId || ''),
        name: String(name || ''),
      }
      if (schemaContext !== undefined) request.schema_context = String(schemaContext || '')
      return callWails('UpdateWorkspace', request)
    }
    return apiService.v1RenameWorkspace(workspaceId, name, schemaContext)
  },

  summary(workspaceId) {
    if (this.isNative()) return callWails('GetWorkspaceSummary', String(workspaceId || ''))
    return apiService.v1GetWorkspaceSummary(workspaceId)
  },

  delete(workspaceId) {
    if (this.isNative()) return callWails('DeleteWorkspace', String(workspaceId || ''))
    return apiService.v1DeleteWorkspace(workspaceId)
  },

  listDeletionJobs() {
    if (this.isNative()) return Promise.resolve({ jobs: [] })
    return apiService.v1ListWorkspaceDeletionJobs()
  },
}

export default workspaceService
