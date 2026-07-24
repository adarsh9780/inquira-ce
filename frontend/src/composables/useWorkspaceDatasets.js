import { filenameFromPath } from '../utils/pathUtils'

export function useWorkspaceDatasets({ columnCounts, fileSizes } = {}) {
  function normalizeDatasetName(value) {
    return String(value || '').trim()
  }

  function datasetRowCount(dataset) {
    const value = Number(dataset?.row_count || 0)
    return Number.isFinite(value) && value > 0 ? value.toLocaleString() : '?'
  }

  function datasetColumnCount(dataset) {
    const value = Number(columnCounts?.value?.[dataset?.table_name] || 0)
    return Number.isFinite(value) && value > 0 ? value : '?'
  }

  function datasetFileSize(dataset) {
    const bytes = Number(fileSizes?.value?.[dataset?.table_name] || 0)
    if (!Number.isFinite(bytes) || bytes <= 0) return null
    if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`
    if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${bytes} B`
  }

  function datasetMetadata(dataset) {
    const segments = [
      `${datasetRowCount(dataset)} rows`,
      `${datasetColumnCount(dataset)} cols`,
    ]
    const sizeLabel = datasetFileSize(dataset)
    if (sizeLabel) segments.push(sizeLabel)
    return segments.join(' · ')
  }

  function datasetSchemaStatusState(dataset) {
    const persistedStatus = String(dataset?.schema_status || 'queued').trim().toLowerCase()
    return ['queued', 'generating', 'ready', 'failed'].includes(persistedStatus)
      ? persistedStatus
      : 'queued'
  }

  function datasetSchemaStatusLabel(dataset) {
    const status = datasetSchemaStatusState(dataset)
    if (status === 'generating') return 'Generating schema'
    if (status === 'ready') return 'Schema ready'
    if (status === 'failed') return 'Schema failed'
    return 'Schema queued'
  }

  function datasetSchemaStatusBadgeClass(dataset) {
    const status = datasetSchemaStatusState(dataset)
    if (status === 'generating') return 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
    if (status === 'ready') return 'bg-[var(--color-success-bg)] text-[var(--color-success)]'
    if (status === 'failed') return 'bg-[var(--color-danger-bg)] text-[var(--color-danger)]'
    return 'bg-[var(--color-base-muted)] text-[var(--color-text-muted)]'
  }

  function formatFilename(raw) {
    const value = String(raw || '').trim()
    return value ? filenameFromPath(value, value) : 'dataset'
  }

  function formatCreatedDate(raw) {
    const parsed = new Date(String(raw || '').trim())
    if (Number.isNaN(parsed.getTime())) return '—'
    return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  }

  function formatRelativeTime(raw) {
    const parsed = new Date(String(raw || '').trim())
    if (Number.isNaN(parsed.getTime())) return 'unknown'
    const minutes = Math.max(1, Math.round((Date.now() - parsed.getTime()) / 60000))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.round(minutes / 60)
    return hours < 48 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`
  }

  return {
    normalizeDatasetName,
    datasetRowCount,
    datasetColumnCount,
    datasetFileSize,
    datasetMetadata,
    datasetSchemaStatusState,
    datasetSchemaStatusLabel,
    datasetSchemaStatusBadgeClass,
    formatFilename,
    formatCreatedDate,
    formatRelativeTime,
  }
}
