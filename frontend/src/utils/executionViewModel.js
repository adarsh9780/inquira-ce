import { normalizePlotlyFigure } from './figurePayload.js'

function parseObjectBucket(bucket, { parseJson = false } = {}) {
  if (!bucket || typeof bucket !== 'object') {
    return { entries: [], rawCount: 0, failed: 0 }
  }

  let failed = 0
  const entries = []

  for (const [name, value] of Object.entries(bucket)) {
    try {
      const parsedValue = parseJson && typeof value === 'string' ? JSON.parse(value) : value
      entries.push({ name, value: parsedValue })
    } catch (_error) {
      failed += 1
    }
  }

  return { entries, rawCount: Object.keys(bucket).length, failed }
}

function dedupeByName(items = []) {
  const seen = new Set()
  return items.filter((item) => {
    const key = String(item?.name || '').trim().toLowerCase()
    if (!key) return false
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function normalizePreviewRows(rows, columns) {
  if (!Array.isArray(rows)) return []
  const names = Array.isArray(columns) ? columns.filter(Boolean).map((col) => String(col)) : []
  return rows
    .map((row) => {
      if (row && typeof row === 'object' && !Array.isArray(row)) return { ...row }
      if (!Array.isArray(row) || names.length === 0) return null
      const mapped = {}
      names.forEach((column, idx) => {
        mapped[column] = row[idx]
      })
      return mapped
    })
    .filter(Boolean)
}

function buildArtifactDataframes(artifacts) {
  if (!Array.isArray(artifacts)) return []
  return artifacts
    .filter((item) => String(item?.kind || '').toLowerCase() === 'dataframe')
    .map((item, index) => {
      const schema = Array.isArray(item?.schema) ? item.schema : []
      const columns = schema
        .map((column) => String(column?.name || ''))
        .filter(Boolean)
      const previewRows = normalizePreviewRows(item?.preview_rows, columns)
      const logicalName = String(item?.logical_name || '').trim()
      const name = logicalName || `dataframe_${index + 1}`
      return {
        name,
        data: {
          artifact_id: item?.artifact_id || null,
          logical_name: logicalName || undefined,
          row_count: Number.isFinite(Number(item?.row_count)) ? Number(item.row_count) : previewRows.length,
          columns,
          data: previewRows,
        },
      }
    })
}

function buildArtifactFigures(artifacts) {
  if (!Array.isArray(artifacts)) return []
  return artifacts
    .filter((item) => String(item?.kind || '').toLowerCase() === 'figure')
    .map((item, index) => {
      const payload = item?.payload?.figure ?? item?.payload
      const normalizedFigure = normalizePlotlyFigure(payload)
      if (!normalizedFigure) return null
      const logicalName = String(item?.logical_name || '').trim()
      const artifactId = String(item?.artifact_id || normalizedFigure?.artifact_id || '').trim()
      return {
        name: logicalName || `figure_${index + 1}`,
        artifact_id: artifactId || undefined,
        logical_name: logicalName || undefined,
        data: normalizedFigure,
      }
    })
    .filter(Boolean)
}

function buildArtifactScalars(artifacts) {
  if (!Array.isArray(artifacts)) return []
  return artifacts
    .filter((item) => String(item?.kind || '').toLowerCase() === 'scalar')
    .map((item, index) => {
      const logicalName = String(item?.logical_name || '').trim()
      const payload = item?.payload
      const value = payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'value')
        ? payload.value
        : payload
      return {
        name: logicalName || `scalar_${index + 1}`,
        value,
      }
    })
}

export function buildExecutionViewModel(response, options = {}) {
  const opts = {
    dataframeLine: (count) => `✅ ${count} dataframe(s) found. Available in Table tab.`,
    figureLine: (count) => `✅ ${count} figure(s) found. Available in Chart tab.`,
    scalarLine: (count) => `✅ ${count} scalar(s) captured.`,
    dataframeParseErrorLine: '⚠️ Failed to parse dataframe data.',
    figureParseErrorLine: '⚠️ Failed to parse figure data.',
    scalarParseErrorLine: '⚠️ Failed to parse scalar data.',
    successLine: '✅ Cell executed successfully!',
    includeVariableSummary: false,
    variableSummaryLine: (counts) =>
      `Variables created: ${counts.dataframes} dataframe(s), ${counts.figures} figure(s), ${counts.scalars} scalar(s)`,
    ...options,
  }

  const outputParts = []

  if (Number.isFinite(response?.execution_time)) {
    outputParts.push(`Execution time: ${response.execution_time.toFixed(3)}s`)
  }

  if (response?.output) {
    outputParts.push(`Output:\n${response.output}`)
  }

  if (response?.error) {
    outputParts.push(`Error: ${response.error}`)
  }

  const parsedDataframes = parseObjectBucket(response?.variables?.dataframes, { parseJson: true })
  const parsedFigures = parseObjectBucket(response?.variables?.figures, { parseJson: true })
  const parsedScalars = parseObjectBucket(response?.variables?.scalars)

  const parsedDataframeEntries = parsedDataframes.entries.map(({ name, value }) => ({ name, data: value }))
  const parsedFigureEntries = parsedFigures.entries
    .map(({ name, value }) => {
      const normalizedFigure = normalizePlotlyFigure(value)
      if (!normalizedFigure) return null
      const artifactId = String(value?.artifact_id || normalizedFigure?.artifact_id || '').trim()
      const logicalName = String(value?.logical_name || value?.name || '').trim()
      return {
        name,
        artifact_id: artifactId || undefined,
        logical_name: logicalName || undefined,
        data: normalizedFigure,
      }
    })
    .filter(Boolean)
  const parsedScalarEntries = parsedScalars.entries.map(({ name, value }) => ({ name, value }))

  const artifactDataframes = buildArtifactDataframes(response?.artifacts)
  const artifactFigures = buildArtifactFigures(response?.artifacts)
  const artifactScalars = buildArtifactScalars(response?.artifacts)

  const mergedDataframes = dedupeByName([...artifactDataframes, ...parsedDataframeEntries])
  const mergedFigures = dedupeByName([...artifactFigures, ...parsedFigureEntries])
  const mergedScalars = dedupeByName([...artifactScalars, ...parsedScalarEntries])

  if (mergedDataframes.length > 0) {
    outputParts.push(opts.dataframeLine(mergedDataframes.length))
  }
  if (parsedDataframes.failed > 0) {
    outputParts.push(opts.dataframeParseErrorLine)
  }

  if (mergedFigures.length > 0) {
    outputParts.push(opts.figureLine(mergedFigures.length))
  }
  if (parsedFigures.failed > 0) {
    outputParts.push(opts.figureParseErrorLine)
  }

  if (mergedScalars.length > 0) {
    outputParts.push(opts.scalarLine(mergedScalars.length))
  }
  if (parsedScalars.failed > 0) {
    outputParts.push(opts.scalarParseErrorLine)
  }

  if (opts.includeVariableSummary) {
    outputParts.push(
      opts.variableSummaryLine({
        dataframes: mergedDataframes.length,
        figures: mergedFigures.length,
        scalars: mergedScalars.length,
      }),
    )
  }

  if (!response?.error && opts.successLine) {
    outputParts.push(opts.successLine)
  }

  return {
    output: outputParts.join('\n\n'),
    dataframes: mergedDataframes,
    figures: mergedFigures,
    scalars: mergedScalars,
    counts: {
      dataframes: mergedDataframes.length,
      figures: mergedFigures.length,
      scalars: mergedScalars.length,
    },
  }
}
