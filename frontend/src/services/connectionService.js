function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function callWails(method, ...args) {
  const app = wailsApp()
  if (!app || typeof app[method] !== 'function') {
    throw new Error(`Wails connection bridge method is unavailable: ${method}`)
  }
  return app[method](...args)
}

function nativeOnly() {
  return Promise.reject(new Error('The connection model is available in the Wails application.'))
}

export const connectionService = {
  isNative() {
    return !!wailsApp()
  },

  chooseFile() {
    if (this.isNative()) return callWails('ChooseLocalConnectionFile')
    return nativeOnly()
  },

  list(workspaceId) {
    if (this.isNative()) return callWails('ListConnections', String(workspaceId || ''))
    return nativeOnly()
  },

  discover(adapterKind, sourcePath, options = {}) {
    if (this.isNative()) {
      const request = {
        adapter_kind: String(adapterKind || ''),
        source_path: String(sourcePath || ''),
      }
      if (options && Object.keys(options).length) request.options = options
      return callWails('DiscoverLocalConnection', request)
    }
    return nativeOnly()
  },

  preview(adapterKind, sourcePath, sourceObjectId = '', limit = 25, options = {}) {
    if (this.isNative()) {
      const request = {
        adapter_kind: String(adapterKind || ''),
        source_path: String(sourcePath || ''),
        limit: Number(limit || 25),
      }
      if (sourceObjectId) request.source_object_id = String(sourceObjectId)
      if (options && Object.keys(options).length) request.options = options
      return callWails('PreviewLocalConnection', request)
    }
    return nativeOnly()
  },

  create(payload) {
    if (this.isNative()) return callWails('CreateLocalConnection', payload || {})
    return nativeOnly()
  },

  refresh(connectionId) {
    if (this.isNative()) return callWails('RefreshConnection', String(connectionId || ''))
    return nativeOnly()
  },

  remove(connectionId) {
    if (this.isNative()) return callWails('DeleteConnection', String(connectionId || ''))
    return nativeOnly()
  },
}

export default connectionService
