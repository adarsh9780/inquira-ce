type ArtifactRecord = Record<string, unknown>

export function isArtifactAvailable(artifact: unknown) {
  if (!artifact || typeof artifact !== 'object') return false
  const status = String((artifact as ArtifactRecord).status || '').trim().toLowerCase()
  return status === '' || status === 'active'
}

export function isArtifactPayloadMissingError(error: unknown) {
  const record = (error || {}) as Record<string, any>
  const status = Number(record?.response?.status ?? record?.status ?? 0)
  if (status === 404) return true
  const detail = String(record?.response?.data?.detail || record?.message || error || '').toLowerCase()
  return detail.includes('artifact_payload_missing')
    || detail.includes('artifact payload is missing')
    || detail.includes('artifact not found')
}

export function artifactUnavailableDescription(kind: 'table' | 'chart', count: number) {
  const noun = kind === 'table' ? 'table' : 'chart'
  if (count === 1) {
    return `This saved ${noun} no longer has its local result file. Run the question again to recreate it.`
  }
  return `These ${count} saved ${noun}s no longer have their local result files. Run the question again to recreate them.`
}
