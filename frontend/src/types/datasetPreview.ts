export type DatasetPreviewMode = 'head' | 'tail'

export interface DatasetPreview {
  tableName: string
  columns: string[]
  rows: Array<Record<string, unknown>>
  rowCount: number
  mode: DatasetPreviewMode
  offset: number
  limit: number
}
