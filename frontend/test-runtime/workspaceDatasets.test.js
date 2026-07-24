import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useWorkspaceDatasets } from '../src/composables/useWorkspaceDatasets'

describe('useWorkspaceDatasets', () => {
  it('formats dataset metadata from workspace enrichment maps', () => {
    const datasets = useWorkspaceDatasets({
      columnCounts: ref({ sales: 8 }),
      fileSizes: ref({ sales: 2048 }),
    })

    expect(datasets.datasetMetadata({ table_name: 'sales', row_count: 1250 }))
      .toBe('1,250 rows · 8 cols · 2.0 KB')
  })

  it('normalizes schema status labels and classes', () => {
    const datasets = useWorkspaceDatasets()

    expect(datasets.datasetSchemaStatusState({ schema_status: 'READY' })).toBe('ready')
    expect(datasets.datasetSchemaStatusLabel({ schema_status: 'failed' })).toBe('Schema failed')
    expect(datasets.datasetSchemaStatusBadgeClass({ schema_status: 'unknown' }))
      .toContain('color-base-muted')
  })

  it('provides stable display fallbacks', () => {
    const datasets = useWorkspaceDatasets()

    expect(datasets.formatFilename('')).toBe('dataset')
    expect(datasets.formatCreatedDate('invalid')).toBe('—')
    expect(datasets.formatRelativeTime('invalid')).toBe('unknown')
  })
})
