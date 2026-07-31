import { hasNativeBridge, invokeNative } from './native.ts'

type RecordValue = Record<string, unknown>

export const workspaceApi = {
  isAvailable: hasNativeBridge,
  async list() {
    if (!hasNativeBridge()) return []
    return invokeNative('ListWorkspaces')
  },
  create(name: unknown, schemaContext: unknown = '') {
    return invokeNative('CreateWorkspace', {
      name: String(name || ''),
      schema_context: String(schemaContext || ''),
    })
  },
  activate(workspaceId: unknown) {
    return invokeNative('ActivateWorkspace', String(workspaceId || ''))
  },
  update(workspaceId: unknown, name: unknown, schemaContext: unknown = undefined) {
    return invokeNative('UpdateWorkspace', {
      workspace_id: String(workspaceId || ''),
      name: String(name || ''),
      ...(schemaContext === undefined ? {} : { schema_context: String(schemaContext || '') }),
    })
  },
  summary(workspaceId: unknown) {
    return invokeNative('GetWorkspaceSummary', String(workspaceId || ''))
  },
  remove(workspaceId: unknown) {
    return invokeNative('DeleteWorkspace', String(workspaceId || ''))
  },
  getAIConfig(workspaceId: unknown) {
    return invokeNative('GetWorkspaceAIConfig', String(workspaceId || ''))
  },
  updateAIConfig(workspaceId: unknown, payload: RecordValue = {}) {
    return invokeNative('UpdateWorkspaceAIConfig', String(workspaceId || ''), payload)
  },
  listDatasets(workspaceId: unknown) {
    return invokeNative('ListWorkspaceDatasets', String(workspaceId || ''))
  },
  refreshDatasetSources(workspaceId: unknown) {
    return invokeNative('RefreshWorkspaceDatasetSources', String(workspaceId || ''))
  },
  getDatasetSchema(workspaceId: unknown, tableName: unknown) {
    return invokeNative(
      'GetWorkspaceDatasetSchema',
      String(workspaceId || ''),
      String(tableName || ''),
    )
  },
  previewDataset(workspaceId: unknown, tableName: unknown, mode: unknown = 'head') {
    return invokeNative(
      'PreviewWorkspaceDataset',
      String(workspaceId || ''),
      String(tableName || ''),
      String(mode || 'head'),
    )
  },
  saveDatasetSchema(workspaceId: unknown, tableName: unknown, payload: RecordValue = {}) {
    return invokeNative('SaveWorkspaceDatasetSchema', {
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      ...(Object.prototype.hasOwnProperty.call(payload, 'context')
        ? { context: String(payload.context || '') }
        : {}),
      ...(Object.prototype.hasOwnProperty.call(payload, 'table_context')
        ? { table_context: String(payload.table_context || '') }
        : {}),
      columns: Array.isArray(payload.columns) ? payload.columns : [],
    })
  },
  saveDatasetContext(workspaceId: unknown, tableName: unknown, context: unknown) {
    return invokeNative('SaveWorkspaceDatasetContext', {
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      context: String(context || ''),
    })
  },
  regenerateDatasetSchema(workspaceId: unknown, tableName: unknown, payload: RecordValue = {}) {
    return invokeNative('RegenerateWorkspaceDatasetSchema', {
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      context: String(payload.context || ''),
      allow_sample_values: Boolean(payload.allow_sample_values),
    })
  },
  async runtimeStatus(workspaceId: unknown) {
    const provision = await invokeNative('RuntimeStatus')
    if (!provision?.ready && !provision?.Ready) return { status: 'error' }
    const kernel = await invokeNative('GetWorkspaceKernelStatus', String(workspaceId || ''))
    const status = String(kernel?.status || '').toLowerCase()
    return { status: ['running', 'busy'].includes(status) ? 'busy' : 'ready' }
  },
}
