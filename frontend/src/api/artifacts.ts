import { invokeNative, withAbortSignal } from './native.ts'

type RecordValue = Record<string, unknown>
type RowsOptions = {
  sortModel?: unknown[]
  filterModel?: RecordValue
  searchText?: string
  signal?: AbortSignal | null
}

const rowsInFlight = new Map<string, Promise<unknown>>()
const rowsCache = new Map<string, unknown>()
const ROWS_CACHE_LIMIT = 200

function clone<T>(payload: T): T {
  return JSON.parse(JSON.stringify(payload ?? null)) as T
}

function readCache(key: string) {
  const cached = rowsCache.get(key)
  if (!cached) return null
  rowsCache.delete(key)
  rowsCache.set(key, cached)
  return clone(cached)
}

function writeCache(key: string, payload: unknown) {
  rowsCache.set(key, clone(payload))
  if (rowsCache.size > ROWS_CACHE_LIMIT) {
    const oldest = rowsCache.keys().next().value
    if (oldest) rowsCache.delete(oldest)
  }
}

async function getRows(
  method: string,
  prefix: string,
  arguments_: unknown[],
  offset: number,
  limit: number,
  options: RowsOptions = {},
) {
  const sortModel = Array.isArray(options.sortModel) ? options.sortModel : []
  const filterModel = options.filterModel && typeof options.filterModel === 'object'
    ? options.filterModel
    : {}
  const searchText = String(options.searchText || '').trim()
  const key = [
    prefix,
    ...arguments_,
    Number(offset || 0),
    Number(limit || 0),
    JSON.stringify(sortModel),
    JSON.stringify(filterModel),
    searchText,
  ].join(':')
  const cached = readCache(key)
  if (cached) return withAbortSignal(Promise.resolve(cached), options.signal || null)
  let request = rowsInFlight.get(key)
  if (!request) {
    request = invokeNative(
      method,
      ...arguments_.map((value) => String(value || '')),
      {
        offset: Number(offset || 0),
        limit: Number(limit || 0),
        sort_model: sortModel,
        filter_model: filterModel,
        search_text: searchText,
      },
    ).then((payload) => {
      writeCache(key, payload)
      return clone(payload)
    }).finally(() => rowsInFlight.delete(key))
    rowsInFlight.set(key, request)
  }
  return withAbortSignal(request, options.signal || null)
}

export const artifactApi = {
  workspaceRows(workspaceId: unknown, artifactId: unknown, offset = 0, limit = 1000, options: RowsOptions = {}) {
    return getRows('GetWorkspaceArtifactRows', 'workspace', [workspaceId, artifactId], offset, limit, options)
  },
  turnRows(
    conversationId: unknown,
    turnId: unknown,
    artifactId: unknown,
    offset = 0,
    limit = 1000,
    options: RowsOptions = {},
  ) {
    return getRows(
      'GetTurnArtifactRows',
      'turn',
      [conversationId, turnId, artifactId],
      offset,
      limit,
      options,
    )
  },
  listTurn(conversationId: unknown, turnId: unknown, kind = 'dataframe') {
    return invokeNative<unknown[]>(
      'ListTurnArtifactSummaries',
      String(conversationId || ''),
      String(turnId || ''),
      String(kind || ''),
    )
  },
  metadata(conversationId: unknown, turnId: unknown, artifactId: unknown) {
    return invokeNative<RecordValue>(
      'GetTurnArtifactMetadata',
      String(conversationId || ''),
      String(turnId || ''),
      String(artifactId || ''),
    )
  },
  remove(conversationId: unknown, turnId: unknown, artifactId: unknown) {
    return invokeNative<RecordValue>(
      'DeleteTurnArtifact',
      String(conversationId || ''),
      String(turnId || ''),
      String(artifactId || ''),
    )
  },
  clearRowsCache() {
    rowsCache.clear()
    rowsInFlight.clear()
  },
}
