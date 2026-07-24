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

function nativeOnly(): Promise<never> {
  return Promise.reject(new Error('The connection model is available in the Wails application.'))
}

export const connectionService = {
  isNative() {
    return Boolean(nativeApp())
  },

  chooseFile() {
    if (this.isNative()) return callWails('ChooseLocalConnectionFile')
    return nativeOnly()
  },

  list(workspaceId: unknown) {
    if (this.isNative()) return callWails('ListConnections', String(workspaceId || ''))
    return nativeOnly()
  },

  discover(adapterKind: unknown, sourcePath: unknown, options: NativeRecord = {}) {
    if (this.isNative()) {
      const request: NativeRecord = {
        adapter_kind: String(adapterKind || ''),
        source_path: String(sourcePath || ''),
      }
      if (options && Object.keys(options).length) request.options = options
      return callWails('DiscoverLocalConnection', request)
    }
    return nativeOnly()
  },

  preview(
    adapterKind: unknown,
    sourcePath: unknown,
    sourceObjectId: unknown = '',
    limit: unknown = 25,
    options: NativeRecord = {},
  ) {
    if (this.isNative()) {
      const request: NativeRecord = {
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

  create(payload: NativeRecord) {
    if (this.isNative()) return callWails('CreateLocalConnection', payload || {})
    return nativeOnly()
  },

  refresh(connectionId: unknown) {
    if (this.isNative()) return callWails('RefreshConnection', String(connectionId || ''))
    return nativeOnly()
  },

  remove(connectionId: unknown) {
    if (this.isNative()) return callWails('DeleteConnection', String(connectionId || ''))
    return nativeOnly()
  },
}

export default connectionService
