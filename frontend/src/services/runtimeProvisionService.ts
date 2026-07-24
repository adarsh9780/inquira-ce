import { invokeNative, nativeApp } from '../api/native'
import type {
  NativeArguments,
  NativeMethodName,
  NativeRecord,
  NativeResult,
} from '../types/native'

function callWails<Method extends NativeMethodName>(
  method: Method,
  ...arguments_: NativeArguments<Method>
): Promise<NativeResult<Method>> {
  return invokeNative(method, ...arguments_)
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

  provision(config: NativeRecord) {
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
