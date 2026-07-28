import { EventsOn, invokeNative, nativeApp } from '../api/native'
import type {
  NativeArguments,
  NativeMethodName,
  NativeRecord,
  NativeResult,
} from '../types/native'

export interface RuntimeProgress {
  operation: 'setup' | 'repair' | 'reset' | 'rollback'
  stage: string
  message: string
  state: 'running' | 'completed' | 'failed'
  current: number
  total: number
  percent: number
}

function callWails<Method extends NativeMethodName>(
  method: Method,
  ...arguments_: NativeArguments<Method>
): Promise<NativeResult<Method>> {
  return invokeNative(method, ...arguments_)
}

async function withRuntimeProgress<Result>(
  operation: () => Promise<Result>,
  onProgress: ((progress: RuntimeProgress) => void) | null = null,
): Promise<Result> {
  const unsubscribe = onProgress
    ? EventsOn('runtime-provision-progress', (payload: unknown) => {
      if (!payload || typeof payload !== 'object') return
      onProgress(payload as RuntimeProgress)
    })
    : () => {}
  try {
    return await operation()
  } finally {
    unsubscribe()
  }
}

export const runtimeProvisionService = {
  isNative() {
    return Boolean(nativeApp())
  },

  status() {
    if (this.isNative()) return callWails('RuntimeStatus')
    return Promise.resolve({ ready: true })
  },

  plan(config: NativeRecord) {
    if (this.isNative()) return callWails('RuntimePlan', config || {})
    return Promise.reject(new Error('Runtime planning is available in the Wails application.'))
  },

  provision(config: NativeRecord, onProgress: ((progress: RuntimeProgress) => void) | null = null) {
    if (this.isNative()) {
      return withRuntimeProgress(() => callWails('ProvisionRuntime', config || {}), onProgress)
    }
    return Promise.reject(new Error('Runtime provisioning is available in the Wails application.'))
  },

  cancel() {
    if (this.isNative()) return callWails('CancelRuntimeProvisioning')
    return Promise.resolve(false)
  },

  repair(onProgress: ((progress: RuntimeProgress) => void) | null = null) {
    if (this.isNative()) {
      return withRuntimeProgress(() => callWails('RepairRuntime'), onProgress)
    }
    return Promise.reject(new Error('Runtime repair is available in the Wails application.'))
  },

  reset(onProgress: ((progress: RuntimeProgress) => void) | null = null) {
    if (this.isNative()) {
      return withRuntimeProgress(() => callWails('ResetRuntime'), onProgress)
    }
    return Promise.reject(new Error('Runtime reset is available in the Wails application.'))
  },

  rollback(onProgress: ((progress: RuntimeProgress) => void) | null = null) {
    if (this.isNative()) {
      return withRuntimeProgress(() => callWails('RollbackRuntime'), onProgress)
    }
    return Promise.reject(new Error('Runtime rollback is available in the Wails application.'))
  },

  exportDiagnostics() {
    if (this.isNative()) return callWails('ExportRuntimeDiagnostics')
    return Promise.reject(new Error('Runtime diagnostics are available in the Wails application.'))
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
