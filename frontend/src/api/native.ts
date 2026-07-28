import type {
  NativeApp,
  NativeArguments,
  NativeMethod,
  NativeMethodName,
  NativeResult,
} from '../types/native'

export function nativeApp(): NativeApp | null {
  if (typeof window === 'undefined') return null
  return (window.go?.main?.App || null) as NativeApp | null
}

export function hasNativeBridge() {
  return Boolean(nativeApp())
}

export function EventsOn(
  eventName: string,
  callback: (...data: unknown[]) => void,
): () => void {
  if (typeof window === 'undefined') return () => {}
  const unsubscribe = window.runtime?.EventsOnMultiple?.(eventName, callback, -1)
  return typeof unsubscribe === 'function' ? unsubscribe : () => {}
}

export function requireNativeMethod<Method extends NativeMethodName>(
  method: Method,
): NativeMethod<Method> {
  const app = nativeApp()
  const candidate = app?.[method]
  if (typeof candidate !== 'function') {
    throw new Error(`The ${method} desktop bridge is unavailable. Open this feature in the installed app.`)
  }
  return candidate.bind(app) as NativeMethod<Method>
}

export function invokeNative<Method extends NativeMethodName>(
  method: Method,
  ...arguments_: NativeArguments<Method>
): Promise<NativeResult<Method>> {
  const invoke = requireNativeMethod(method) as (
    ...values: NativeArguments<Method>
  ) => Promise<NativeResult<Method>>
  return invoke(...arguments_)
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
