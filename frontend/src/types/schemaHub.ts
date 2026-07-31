export interface SchemaHubColumn {
  name: string
  dataType: string
  nullable: boolean
  description: string
  aliases: string[]
  tableId: string
  tableName: string
}

export interface SchemaHubTable {
  id: string
  tableName: string
  tableContext?: string
  rowCount: number
  status: string
  columns: SchemaHubColumn[]
}

export type SchemaHubSelection =
  | { kind: 'workspace' }
  | { kind: 'sources' }
  | { kind: 'table'; tableId: string }
