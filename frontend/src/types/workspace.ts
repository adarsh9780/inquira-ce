import type { ConnectionId, WorkspaceId } from './identifiers'

export interface WorkspaceSummary {
  id: WorkspaceId
  name: string
  schema_context?: string
  is_active?: boolean
  table_count: number
  table_names: string[]
  created_at?: string
  updated_at?: string
}

export type LocalConnectionKind = 'csv' | 'parquet' | 'excel'
export type ConnectionStatus = 'discovering' | 'ready' | 'refreshing' | 'failed'

export interface ConnectionSummary {
  id: ConnectionId
  workspace_id: WorkspaceId
  name: string
  adapter_kind: LocalConnectionKind
  source_path: string
  selected_object_ids: string[]
  table_names: string[]
  status: ConnectionStatus
  error?: string
  refreshed_at?: string
}

export interface DatasetColumn {
  name: string
  data_type: string
  nullable?: boolean
  description?: string
  aliases?: string[]
}

export interface DatasetSummary {
  name: string
  row_count?: number
  columns: DatasetColumn[]
  schema_ready?: boolean
}

export type WorkspaceReadiness =
  | { state: 'no_workspace'; ready: false }
  | { state: 'no_data'; ready: false }
  | { state: 'model_connection_required'; ready: false }
  | { state: 'workspace_configuration_required'; ready: false }
  | { state: 'ready'; ready: true }
