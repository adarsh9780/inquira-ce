import { hasNativeBridge, invokeNative } from './native.ts'

type RecordValue = Record<string, unknown>

export const workspaceApi = {
  isAvailable: hasNativeBridge,
  async list() {
    if (!hasNativeBridge()) return []
    return invokeNative<unknown[]>('ListWorkspaces')
  },
  create(name: unknown, schemaContext: unknown = '') {
    return invokeNative<RecordValue>('CreateWorkspace', {
      name: String(name || ''),
      schema_context: String(schemaContext || ''),
    })
  },
  activate(workspaceId: unknown) {
    return invokeNative<RecordValue>('ActivateWorkspace', String(workspaceId || ''))
  },
  update(workspaceId: unknown, name: unknown, schemaContext: unknown = undefined) {
    return invokeNative<RecordValue>('UpdateWorkspace', {
      workspace_id: String(workspaceId || ''),
      name: String(name || ''),
      ...(schemaContext === undefined ? {} : { schema_context: String(schemaContext || '') }),
    })
  },
  summary(workspaceId: unknown) {
    return invokeNative<RecordValue>('GetWorkspaceSummary', String(workspaceId || ''))
  },
  remove(workspaceId: unknown) {
    return invokeNative<RecordValue>('DeleteWorkspace', String(workspaceId || ''))
  },
  getAIConfig(workspaceId: unknown) {
    return invokeNative<RecordValue>('GetWorkspaceAIConfig', String(workspaceId || ''))
  },
  updateAIConfig(workspaceId: unknown, payload: RecordValue = {}) {
    return invokeNative<RecordValue>('UpdateWorkspaceAIConfig', String(workspaceId || ''), payload)
  },
  listDatasets(workspaceId: unknown) {
    return invokeNative<RecordValue>('ListWorkspaceDatasets', String(workspaceId || ''))
  },
  getDatasetSchema(workspaceId: unknown, tableName: unknown) {
    return invokeNative<RecordValue>(
      'GetWorkspaceDatasetSchema',
      String(workspaceId || ''),
      String(tableName || ''),
    )
  },
  saveDatasetSchema(workspaceId: unknown, tableName: unknown, payload: RecordValue = {}) {
    return invokeNative<RecordValue>('SaveWorkspaceDatasetSchema', {
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      ...(Object.prototype.hasOwnProperty.call(payload, 'context')
        ? { context: String(payload.context || '') }
        : {}),
      columns: Array.isArray(payload.columns) ? payload.columns : [],
    })
  },
  regenerateDatasetSchema(workspaceId: unknown, tableName: unknown, payload: RecordValue = {}) {
    return invokeNative<RecordValue>('RegenerateWorkspaceDatasetSchema', {
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      context: String(payload.context || ''),
      allow_sample_values: Boolean(payload.allow_sample_values),
    })
  },
  async runtimeStatus(workspaceId: unknown) {
    const provision = await invokeNative<RecordValue>('RuntimeStatus')
    if (!provision?.ready && !provision?.Ready) return { status: 'error' }
    const kernel = await invokeNative<RecordValue>('GetWorkspaceKernelStatus', String(workspaceId || ''))
    const status = String(kernel?.status || '').toLowerCase()
    return { status: ['running', 'busy'].includes(status) ? 'busy' : 'ready' }
  },
}
