import type { ArtifactId, RunId, TurnId, WorkspaceId } from './identifiers'

interface ArtifactBase {
  id: ArtifactId
  workspace_id: WorkspaceId
  turn_id?: TurnId
  run_id?: RunId
  logical_name: string
  created_at?: string
  promoted?: boolean
}

export interface DataframeArtifact extends ArtifactBase {
  kind: 'dataframe'
  columns?: string[]
  row_count?: number
  preview?: Record<string, unknown>[]
}

export interface FigureArtifact extends ArtifactBase {
  kind: 'figure'
  figure?: {
    data: unknown[]
    layout?: Record<string, unknown>
    config?: Record<string, unknown>
  }
}

export interface ChartSpecArtifact extends ArtifactBase {
  kind: 'chart_spec'
  value: {
    schema: 'inquira.chart/v1'
    data: { logical_name: string; artifact_id?: string | null }
    mark: string
    encoding: Record<string, unknown>
    title: string
    description?: string | null
    options?: Record<string, unknown>
  }
}

export interface ScalarArtifact extends ArtifactBase {
  kind: 'scalar'
  value: unknown
}

export interface JsonArtifact extends ArtifactBase {
  kind: 'json'
  value: unknown
}

export interface TextArtifact extends ArtifactBase {
  kind: 'text'
  text: string
}

export type Artifact = DataframeArtifact | FigureArtifact | ChartSpecArtifact | ScalarArtifact | JsonArtifact | TextArtifact

export interface TableSort {
  columnId: string
  direction: 'asc' | 'desc'
}

export interface TableFilter {
  columnId: string
  kind: 'text' | 'number' | 'boolean'
  operator: string
  value?: string | number | boolean
  valueTo?: string | number
}

export interface TablePage {
  rows: Record<string, unknown>[]
  columns: string[]
  rowCount: number
  pageIndex: number
  pageSize: number
  sorting: TableSort[]
  filters: TableFilter[]
}
