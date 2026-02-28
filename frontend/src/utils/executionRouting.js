function normalizeRows(value) {
  if (!value) return null
  if (Array.isArray(value)) return value
  if (typeof value !== 'object') return null

  const data = Array.isArray(value.data) ? value.data : null
  if (!data) return null

  if (data.length === 0) return []
  if (typeof data[0] === 'object' && !Array.isArray(data[0])) return data

  const columns = Array.isArray(value.columns) ? value.columns : []
  if (!columns.length) return null

  return data.map((row) => {
    if (!Array.isArray(row)) return row
    const mapped = {}
    columns.forEach((col, idx) => {
      mapped[col] = row[idx]
    })
    return mapped
  })
}

function sampleSignature(rows) {
  if (!Array.isArray(rows)) return ''
  const sample = rows.slice(0, 3)
  return JSON.stringify(sample)
}

function figureSignature(figure) {
  if (!figure || typeof figure !== 'object') return ''
  const traces = Array.isArray(figure.data) ? figure.data.slice(0, 2) : []
  const layoutTitle = figure.layout?.title?.text || figure.layout?.title || ''
  return JSON.stringify({ traces, layoutTitle })
}

export function resolvePreferredArtifactNames(viewModel, normalized) {
  const resultKind = String(normalized?.result_kind || '').toLowerCase()
  const resultType = String(normalized?.result_type || '').toLowerCase()
  const resultName = String(normalized?.result_name || '').trim()
  const result = normalized?.result

  let dataframeName = null
  if (resultName && Array.isArray(viewModel?.dataframes) && viewModel.dataframes.some((df) => df?.name === resultName)) {
    dataframeName = resultKind === 'dataframe' ? resultName : null
  }
  if (!dataframeName && (resultKind === 'dataframe' || resultType === 'dataframe') && Array.isArray(viewModel?.dataframes)) {
    const targetRows = normalizeRows(result)
    const targetSig = sampleSignature(targetRows)
    if (targetSig) {
      const match = viewModel.dataframes.find((df) => {
        const candidateRows = normalizeRows(df?.data)
        return sampleSignature(candidateRows) === targetSig
      })
      dataframeName = match?.name || null
    }
  }

  let figureName = null
  if (resultName && Array.isArray(viewModel?.figures) && viewModel.figures.some((fig) => fig?.name === resultName)) {
    figureName = resultKind === 'figure' ? resultName : null
  }
  if (!figureName && (resultKind === 'figure' || resultType === 'figure') && Array.isArray(viewModel?.figures)) {
    const targetSig = figureSignature(result)
    if (targetSig) {
      const match = viewModel.figures.find((fig) => figureSignature(fig?.data) === targetSig)
      figureName = match?.name || null
    }
  }

  return { dataframeName, figureName }
}

export function prioritizeByName(items, preferredName) {
  if (!Array.isArray(items) || !items.length || !preferredName) return Array.isArray(items) ? items : []
  const idx = items.findIndex((item) => item?.name === preferredName)
  if (idx <= 0) return items
  const copy = [...items]
  const [picked] = copy.splice(idx, 1)
  copy.unshift(picked)
  return copy
}

export function decideExecutionTab({ resultType, resultKind, hasError, hasDataframes, hasFigures }) {
  if (hasError) return 'terminal'
  const normalizedKind = String(resultKind || '').toLowerCase()
  if (normalizedKind === 'dataframe' && hasDataframes) return 'table'
  if (normalizedKind === 'figure' && hasFigures) return 'figure'
  const normalized = String(resultType || '').toLowerCase()
  if (normalized === 'dataframe' && hasDataframes) return 'table'
  if (normalized === 'figure' && hasFigures) return 'figure'
  return null
}

function extractIdentifier(code) {
  const trimmed = String(code || '').trim()
  if (!trimmed) return null
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(trimmed)) return null
  return trimmed
}

export function decideExecutionTabWithSelection({
  resultType,
  resultKind,
  resultName,
  hasError,
  hasDataframes,
  hasFigures,
  selectedCode,
  dataframeNames = [],
  figureNames = [],
}) {
  const primary = decideExecutionTab({ resultType, resultKind, hasError, hasDataframes, hasFigures })
  if (primary) return primary

  const normalizedKind = String(resultKind || '').toLowerCase()
  const named = String(resultName || '').trim()
  if (named && normalizedKind === 'dataframe' && dataframeNames.includes(named)) return 'table'
  if (named && normalizedKind === 'figure' && figureNames.includes(named)) return 'figure'

  const ref = extractIdentifier(selectedCode)
  if (!ref) return null
  if (dataframeNames.includes(ref)) return 'table'
  if (figureNames.includes(ref)) return 'figure'
  return null
}
