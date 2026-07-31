type NativeRecord = Record<string, unknown>

export interface SchemaRefreshFailure {
  connectionName: string
  message: string
}

export interface SchemaRefreshResult {
  attempted: number
  succeeded: number
  changed: number
  failures: SchemaRefreshFailure[]
}

function count(value: unknown): number {
  const number = Number(value)
  return Number.isFinite(number) ? Math.max(0, Math.trunc(number)) : 0
}

export function normalizeSchemaRefreshResult(value: unknown): SchemaRefreshResult {
  const result = value && typeof value === 'object' ? value as NativeRecord : {}
  const attempted = count(result.attempted)
  const succeeded = Math.min(attempted, count(result.succeeded))
  const changed = Math.min(succeeded, count(result.changed))
  const failures = (Array.isArray(result.failures) ? result.failures : []).map((item) => {
    const failure = item && typeof item === 'object' ? item as NativeRecord : {}
    return {
      connectionName: String(failure.connection_name || '').trim(),
      message: String(failure.message || '').trim(),
    }
  })
  return { attempted, succeeded, changed, failures }
}

export function schemaRefreshFeedback(result: SchemaRefreshResult) {
  if (result.attempted === 0) {
    return { type: 'info' as const, title: 'No data sources to refresh', message: 'Add a data source to populate the workspace schema.' }
  }
  if (result.failures.length) {
    const names = result.failures.map((failure) => failure.connectionName).filter(Boolean)
    const visible = names.slice(0, 2).join(', ')
    const remaining = Math.max(0, names.length - 2)
    const detail = visible ? ` Check ${visible}${remaining ? ` and ${remaining} more` : ''}.` : ''
    return {
      type: 'warning' as const,
      title: 'Schema partially refreshed',
      message: `${result.succeeded} of ${result.attempted} data ${result.attempted === 1 ? 'source' : 'sources'} refreshed.${detail}`,
    }
  }
  if (result.changed === 0) {
    return { type: 'success' as const, title: 'Schema is up to date', message: `${result.succeeded} data ${result.succeeded === 1 ? 'source' : 'sources'} checked; no changes found.` }
  }
  return { type: 'success' as const, title: 'Schema refreshed', message: `${result.changed} data ${result.changed === 1 ? 'source' : 'sources'} changed and the workspace schema was reloaded.` }
}
