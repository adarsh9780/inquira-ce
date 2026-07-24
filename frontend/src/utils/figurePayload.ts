type RecordValue = Record<string, unknown>

export interface NormalizedPlotlyFigure extends RecordValue {
  data: RecordValue[]
  layout: RecordValue
  frames?: unknown[]
}

function isPlainObject(value: unknown): value is RecordValue {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function safeParseJson(value: unknown): unknown {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed) return null
  try {
    return JSON.parse(trimmed)
  } catch (_error) {
    return null
  }
}

function coerceTraceArray(value: unknown): RecordValue[] | null {
  if (Array.isArray(value)) return value as RecordValue[]
  if (isPlainObject(value)) return [value]
  if (typeof value === 'string') {
    const parsed = safeParseJson(value)
    if (Array.isArray(parsed)) return parsed as RecordValue[]
    if (isPlainObject(parsed)) return [parsed]
  }
  return null
}

function coerceLayout(value: unknown): RecordValue {
  if (isPlainObject(value)) return value
  if (typeof value === 'string') {
    const parsed = safeParseJson(value)
    if (isPlainObject(parsed)) return parsed
  }
  return {}
}

function unwrapFigureContainer(value: unknown): unknown {
  if (!isPlainObject(value)) return value
  if (Object.prototype.hasOwnProperty.call(value, 'figure')) return value.figure
  if (isPlainObject(value.payload) && Object.prototype.hasOwnProperty.call(value.payload, 'figure')) {
    return value.payload.figure
  }
  if (Object.prototype.hasOwnProperty.call(value, 'plotly')) return value.plotly
  return value
}

export function normalizePlotlyFigure(value: unknown): NormalizedPlotlyFigure | null {
  let candidate: unknown = value
  for (let depth = 0; depth < 4; depth += 1) {
    if (typeof candidate === 'string') {
      candidate = safeParseJson(candidate)
      continue
    }

    candidate = unwrapFigureContainer(candidate)
    if (typeof candidate === 'string') {
      candidate = safeParseJson(candidate)
      continue
    }
    if (!isPlainObject(candidate)) return null

    const traces = coerceTraceArray(candidate.data ?? candidate.traces)
    if (!traces) return null

    const normalized: NormalizedPlotlyFigure = {
      ...candidate,
      data: traces,
      layout: coerceLayout(candidate.layout),
    }
    if (Array.isArray(candidate.frames)) {
      normalized.frames = candidate.frames
    }
    return normalized
  }
  return null
}
