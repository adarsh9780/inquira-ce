function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function callWails(method, ...args) {
  const app = wailsApp()
  if (!app || typeof app[method] !== 'function') {
    throw new Error(`Wails runtime bridge method is unavailable: ${method}`)
  }
  return app[method](...args)
}

export const runtimeProvisionService = {
  isNative() {
    return !!wailsApp()
  },

  status() {
    if (this.isNative()) return callWails('RuntimeStatus')
    return Promise.resolve({ ready: true })
  },

  plan(config) {
    if (this.isNative()) return callWails('RuntimePlan', config || {})
    return Promise.reject(new Error('Runtime planning is available in the Wails application.'))
  },

  provision(config) {
    if (this.isNative()) return callWails('ProvisionRuntime', config || {})
    return Promise.reject(new Error('Runtime provisioning is available in the Wails application.'))
  },

  choosePythonExecutable() {
    if (this.isNative()) return callWails('ChoosePythonExecutable')
    return Promise.reject(new Error('Python selection is available in the Wails application.'))
  },

  chooseCertificateBundle() {
    if (this.isNative()) return callWails('ChooseCertificateBundle')
    return Promise.reject(new Error('Certificate selection is available in the Wails application.'))
  },
}

export default runtimeProvisionService
