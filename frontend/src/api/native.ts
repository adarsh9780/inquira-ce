export type NativeMethod = (...arguments_: unknown[]) => Promise<unknown>

export function nativeApp(): Record<string, NativeMethod> | null {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

export function hasNativeBridge() {
  return Boolean(nativeApp())
}

export function requireNativeMethod(method: string): NativeMethod {
  const app = nativeApp()
  const candidate = app?.[method]
  if (typeof candidate !== 'function') {
    throw new Error(`The ${method} desktop bridge is unavailable. Open this feature in the installed app.`)
  }
  return candidate.bind(app)
}

export function invokeNative<T>(method: string, ...arguments_: unknown[]): Promise<T> {
  return requireNativeMethod(method)(...arguments_) as Promise<T>
}

export function createAbortError(message = 'Request aborted') {
  const error = new Error(message)
  error.name = 'AbortError'
  return error
}

export function withAbortSignal<T>(promise: Promise<T>, signal: AbortSignal | null = null): Promise<T> {
  if (!signal) return promise
  if (signal.aborted) return Promise.reject(createAbortError())
  return new Promise((resolve, reject) => {
    const cleanup = () => signal.removeEventListener('abort', onAbort)
    const onAbort = () => {
      cleanup()
      reject(createAbortError())
    }
    signal.addEventListener('abort', onAbort, { once: true })
    promise.then(
      (value) => {
        cleanup()
        resolve(value)
      },
      (error: unknown) => {
        cleanup()
        reject(error)
      },
    )
  })
}
