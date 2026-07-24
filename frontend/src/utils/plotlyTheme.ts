type RecordValue = Record<string, unknown>
type PlotlyThemeMode = 'soft' | 'hard'

interface UiColors {
  base: string
  surface: string
  panelElevated: string
  border: string
  borderHover: string
  textMain: string
  textMuted: string
  accent: string
  chartGrid: string
  chartZero: string
  chartPaper: string
  chartPlot: string
  chartTooltipBg: string
  chartTooltipBorder: string
  fontFamily: string
  colorway: readonly string[]
  sequentialScale: readonly string[]
  divergingScale: readonly string[]
}

const DEFAULT_COLORWAY = Object.freeze([
  '#D47948', // brand orange
  '#3B82F6', // brand blue
  '#0EA5E9', // sky
  '#22C55E', // success green
  '#F59E0B', // warning amber
  '#EF4444', // danger red
  '#14B8A6', // teal
  '#6366F1', // indigo
])

const DEFAULT_SEQUENTIAL_SCALE = Object.freeze([
  '#FFF7ED',
  '#FED7AA',
  '#E7A06A',
  '#D47948',
])

const DEFAULT_DIVERGING_SCALE = Object.freeze([
  '#3B82F6',
  '#FFFFFF',
  '#D47948',
])

const DEFAULT_UI_COLORS = Object.freeze({
  base: '#FFFFFF',
  surface: '#FFFFFF',
  panelElevated: '#FFFFFF',
  border: '#E4E4E7',
  borderHover: '#D4D4D8',
  textMain: '#18181B',
  textMuted: '#52525B',
  accent: '#D47948',
  chartGrid: '#E4E4E7',
  chartZero: '#D4D4D8',
  chartPaper: '#FFFFFF',
  chartPlot: '#FFFFFF',
  chartTooltipBg: '#FFFFFF',
  chartTooltipBorder: '#D4D4D8',
  fontFamily: 'sans-serif',
  colorway: DEFAULT_COLORWAY,
  sequentialScale: DEFAULT_SEQUENTIAL_SCALE,
  divergingScale: DEFAULT_DIVERGING_SCALE,
})

let UI_COLORS: UiColors = { ...DEFAULT_UI_COLORS }

function readUiColor(tokenName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const value = String(getComputedStyle(document.documentElement).getPropertyValue(tokenName) || '').trim()
  return value || fallback
}

function refreshUiColors(): void {
  UI_COLORS = {
    base: readUiColor('--color-base', DEFAULT_UI_COLORS.base),
    surface: readUiColor('--color-surface', DEFAULT_UI_COLORS.surface),
    panelElevated: readUiColor('--color-panel-elevated', DEFAULT_UI_COLORS.panelElevated),
    border: readUiColor('--color-border', DEFAULT_UI_COLORS.border),
    borderHover: readUiColor('--color-border-hover', DEFAULT_UI_COLORS.borderHover),
    textMain: readUiColor('--color-text-main', DEFAULT_UI_COLORS.textMain),
    textMuted: readUiColor('--color-text-muted', DEFAULT_UI_COLORS.textMuted),
    accent: readUiColor('--color-accent', DEFAULT_UI_COLORS.accent),
    chartGrid: readUiColor('--color-chart-grid', DEFAULT_UI_COLORS.chartGrid),
    chartZero: readUiColor('--color-chart-zero', DEFAULT_UI_COLORS.chartZero),
    chartPaper: readUiColor('--color-chart-paper', DEFAULT_UI_COLORS.chartPaper),
    chartPlot: readUiColor('--color-chart-plot', DEFAULT_UI_COLORS.chartPlot),
    chartTooltipBg: readUiColor('--color-chart-tooltip-bg', DEFAULT_UI_COLORS.chartTooltipBg),
    chartTooltipBorder: readUiColor('--color-chart-tooltip-border', DEFAULT_UI_COLORS.chartTooltipBorder),
    fontFamily: readUiColor('--font-ui', DEFAULT_UI_COLORS.fontFamily),
    colorway: DEFAULT_COLORWAY.map((fallback, index) => (
      readUiColor(`--color-chart-series-${index + 1}`, fallback)
    )),
    sequentialScale: DEFAULT_SEQUENTIAL_SCALE.map((fallback, index) => (
      readUiColor(`--color-chart-sequential-${index + 1}`, fallback)
    )),
    divergingScale: [
      readUiColor('--color-chart-diverging-low', DEFAULT_DIVERGING_SCALE[0]),
      readUiColor('--color-chart-diverging-mid', DEFAULT_DIVERGING_SCALE[1]),
      readUiColor('--color-chart-diverging-high', DEFAULT_DIVERGING_SCALE[2]),
    ],
  }
}

const CARTESIAN_AXIS_KEY = /^(x|y)axis(\d+)?$/i
const COLOR_AXIS_KEY = /^coloraxis(\d+)?$/i
const BAR_LIKE_TRACE_TYPES = new Set(['bar', 'histogram', 'funnel', 'waterfall'])

const CARTESIAN_TRACE_TYPES = new Set([
  '',
  'bar',
  'box',
  'candlestick',
  'contour',
  'funnel',
  'heatmap',
  'histogram',
  'ohlc',
  'scatter',
  'scattergl',
  'violin',
  'waterfall',
])

export const PLOTLY_THEME_MODE = Object.freeze({
  SOFT: 'soft',
  HARD: 'hard',
})

function isPlainObject(value: unknown): value is RecordValue {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function cloneArray(value: unknown[]): unknown[] {
  return value.map((item) => {
    if (Array.isArray(item)) return cloneArray(item)
    if (isPlainObject(item)) return mergeDeep({}, item)
    return item
  })
}

function mergeDeep(base: unknown, patch: unknown): RecordValue {
  const baseObject = isPlainObject(base) ? base : {}
  const patchObject = isPlainObject(patch) ? patch : {}
  const merged = { ...baseObject }

  for (const [key, patchValue] of Object.entries(patchObject)) {
    const baseValue = baseObject[key]
    if (isPlainObject(baseValue) && isPlainObject(patchValue)) {
      merged[key] = mergeDeep(baseValue, patchValue)
      continue
    }
    if (isPlainObject(patchValue)) {
      merged[key] = mergeDeep({}, patchValue)
      continue
    }
    if (Array.isArray(patchValue)) {
      merged[key] = cloneArray(patchValue)
      continue
    }
    merged[key] = patchValue
  }

  return merged
}

function normalizeMode(mode: unknown): PlotlyThemeMode {
  return mode === PLOTLY_THEME_MODE.HARD ? PLOTLY_THEME_MODE.HARD : PLOTLY_THEME_MODE.SOFT
}

function uniqueStrings(values: unknown): string[] {
  if (!Array.isArray(values)) return []
  const seen = new Set<string>()
  const output: string[] = []
  for (const value of values) {
    if (typeof value !== 'string') continue
    if (seen.has(value)) continue
    seen.add(value)
    output.push(value)
  }
  return output
}

function hasCartesianData(data: unknown): boolean {
  if (!Array.isArray(data) || data.length === 0) return false
  return data.some((trace) => {
    const traceType = String(isPlainObject(trace) ? trace.type || '' : '').trim().toLowerCase()
    return CARTESIAN_TRACE_TYPES.has(traceType)
  })
}

function getTraceType(trace: unknown, fallback = ''): string {
  return String(isPlainObject(trace) ? trace.type || fallback : fallback).trim().toLowerCase()
}

function countBarLikeTraces(data: unknown): number {
  if (!Array.isArray(data) || data.length === 0) return 0
  return data.reduce((count, trace) => {
    if (!isPlainObject(trace)) return count
    return BAR_LIKE_TRACE_TYPES.has(getTraceType(trace, '')) ? count + 1 : count
  }, 0)
}

function normalizeBarMarker(
  marker: unknown,
  color: string,
  forceSingleColor: boolean,
): RecordValue {
  const source = isPlainObject(marker) ? marker : {}
  const nextMarker = mergeDeep(
    {
      line: {
        color: UI_COLORS.surface,
        width: 1,
      },
    },
    source,
  )

  if (!forceSingleColor) return nextMarker

  nextMarker.color = color
  delete nextMarker.autocolorscale
  delete nextMarker.cauto
  delete nextMarker.cmid
  delete nextMarker.cmin
  delete nextMarker.cmax
  delete nextMarker.coloraxis
  delete nextMarker.colorbar
  delete nextMarker.colorscale
  delete nextMarker.reversescale
  delete nextMarker.showscale
  return nextMarker
}

function applyBarTraceTemplate(data: unknown): unknown[] {
  if (!Array.isArray(data)) return []
  const barLikeTraceCount = countBarLikeTraces(data)
  if (barLikeTraceCount === 0) return data

  return data.map((trace, index) => {
    if (!isPlainObject(trace)) return trace
    const traceType = getTraceType(trace, 'scatter')
    if (!BAR_LIKE_TRACE_TYPES.has(traceType)) return trace

    const color = UI_COLORS.colorway[index % UI_COLORS.colorway.length]
    const marker = isPlainObject(trace.marker) ? trace.marker : {}
    const hasPerItemColor = Array.isArray(marker.color) || Array.isArray(trace.color)
    const hasColorAxis = typeof marker.coloraxis === 'string' || typeof trace.coloraxis === 'string'
    const forceSingleColor = barLikeTraceCount === 1 && (hasPerItemColor || hasColorAxis)

    const nextTrace: RecordValue = {
      ...trace,
      marker: normalizeBarMarker(marker, UI_COLORS.accent, forceSingleColor),
    }

    if (forceSingleColor) {
      delete nextTrace.coloraxis
      if (typeof nextTrace.showscale !== 'undefined') delete nextTrace.showscale
    }

    const nextMarker = isPlainObject(nextTrace.marker) ? nextTrace.marker : {}
    if (!nextMarker.color && !hasPerItemColor && !hasColorAxis) {
      nextTrace.marker = mergeDeep(nextMarker, { color })
    }

    return nextTrace
  })
}

function stripUnusedColorAxis(layout: RecordValue, data: unknown): RecordValue {
  const usesColorAxis = Array.isArray(data) && data.some((traceValue) => {
    if (!isPlainObject(traceValue)) return false
    const marker = isPlainObject(traceValue.marker) ? traceValue.marker : {}
    return typeof traceValue.coloraxis === 'string' || typeof marker.coloraxis === 'string'
  })
  if (usesColorAxis) return layout

  const nextLayout = { ...layout }
  for (const key of Object.keys(nextLayout)) {
    if (COLOR_AXIS_KEY.test(key)) delete nextLayout[key]
  }
  return nextLayout
}

function getSoftAxisPatch(): RecordValue {
  return {
    linecolor: UI_COLORS.chartZero,
    gridcolor: UI_COLORS.chartGrid,
    zerolinecolor: UI_COLORS.chartZero,
    tickcolor: UI_COLORS.textMuted,
    tickfont: {
      color: UI_COLORS.textMuted,
    },
    title: {
      font: {
        color: UI_COLORS.textMain,
      },
    },
  }
}

function getHardAxisPatch(): RecordValue {
  return mergeDeep(getSoftAxisPatch(), {
    automargin: true,
    title: {
      standoff: 10,
      font: {
        family: UI_COLORS.fontFamily,
        size: 12,
      },
    },
    tickfont: {
      family: UI_COLORS.fontFamily,
      size: 11,
    },
  })
}

function applyAxisTheme(
  layout: RecordValue,
  mode: PlotlyThemeMode,
  data: unknown,
): RecordValue {
  const axisPatch = mode === PLOTLY_THEME_MODE.HARD ? getHardAxisPatch() : getSoftAxisPatch()
  const axisKeys = Object.keys(layout).filter((key) => CARTESIAN_AXIS_KEY.test(key))
  const shouldAddDefaultAxes = axisKeys.length === 0 && hasCartesianData(data)
  const nextLayout = { ...layout }

  if (shouldAddDefaultAxes) {
    nextLayout.xaxis = mergeDeep(nextLayout.xaxis, axisPatch)
    nextLayout.yaxis = mergeDeep(nextLayout.yaxis, axisPatch)
    return nextLayout
  }

  for (const axisKey of axisKeys) {
    nextLayout[axisKey] = mergeDeep(nextLayout[axisKey], axisPatch)
  }
  return nextLayout
}

function applyAnnotationTheme(layout: RecordValue, mode: PlotlyThemeMode): RecordValue {
  if (!Array.isArray(layout.annotations) || layout.annotations.length === 0) return layout
  const annotationPatch = mode === PLOTLY_THEME_MODE.HARD
    ? {
        font: {
          family: UI_COLORS.fontFamily,
          size: 11,
          color: UI_COLORS.textMain,
        },
      }
    : {
        font: {
          color: UI_COLORS.textMain,
        },
      }

  return {
    ...layout,
    annotations: layout.annotations.map((annotation) => (
      isPlainObject(annotation) ? mergeDeep(annotation, annotationPatch) : annotation
    )),
  }
}

function getHardMargins(context: string): RecordValue {
  if (context === 'fullscreen') {
    return { l: 64, r: 40, t: 56, b: 56, pad: 4 }
  }
  if (context === 'export') {
    return { l: 56, r: 36, t: 54, b: 50, pad: 4 }
  }
  return { l: 52, r: 28, t: 44, b: 44, pad: 4 }
}

function applyHardTraceDefaults(data: unknown): unknown[] {
  if (!Array.isArray(data)) return []
  return data.map((trace, index) => {
    if (!isPlainObject(trace)) return trace
    const traceType = getTraceType(trace, 'scatter')
    const color = UI_COLORS.colorway[index % UI_COLORS.colorway.length]

    if (traceType === 'bar' || traceType === 'histogram' || traceType === 'funnel' || traceType === 'waterfall') {
      return {
        ...trace,
        marker: mergeDeep(
          {
            color,
            line: {
              color: UI_COLORS.surface,
              width: 1,
            },
          },
          trace.marker,
        ),
      }
    }

    if (traceType === 'scatter' || traceType === 'scattergl') {
      const usesMarkers = !trace.mode || String(trace.mode).includes('markers')
      const themedScatter = {
        ...trace,
        line: mergeDeep(
          {
            color,
            width: 2,
          },
          trace.line,
        ),
      }
      if (!usesMarkers) return themedScatter
      return {
        ...themedScatter,
        marker: mergeDeep(
          {
            color,
            size: 7,
            line: {
              color: UI_COLORS.surface,
              width: 1,
            },
          },
          trace.marker,
        ),
      }
    }

    if (traceType === 'pie' || traceType === 'sunburst' || traceType === 'treemap') {
      return {
        ...trace,
        marker: mergeDeep(
          {
            line: {
              color: UI_COLORS.surface,
              width: 1,
            },
          },
          trace.marker,
        ),
        textfont: mergeDeep(
          {
            color: UI_COLORS.textMain,
          },
          trace.textfont,
        ),
      }
    }

    if (traceType === 'box' || traceType === 'violin') {
      return {
        ...trace,
        line: mergeDeep(
          {
            color,
            width: 2,
          },
          trace.line,
        ),
        marker: mergeDeep(
          {
            color,
          },
          trace.marker,
        ),
      }
    }

    return trace
  })
}

export function applyPlotlyTheme(
  figure: unknown,
  options: { mode?: unknown; context?: unknown } = {},
): RecordValue | null {
  if (!isPlainObject(figure)) return null
  refreshUiColors()

  const mode = normalizeMode(options.mode)
  const context = String(options.context || 'panel').toLowerCase()

  const rawData = Array.isArray(figure.data) ? cloneArray(figure.data) : []
  const rawLayout = isPlainObject(figure.layout) ? mergeDeep({}, figure.layout) : {}
  let themedData = applyBarTraceTemplate(rawData)

  const softLayoutPatch = {
    paper_bgcolor: UI_COLORS.chartPaper,
    plot_bgcolor: UI_COLORS.chartPlot,
    colorway: [...UI_COLORS.colorway],
    colorscale: {
      sequential: [
        [0, UI_COLORS.sequentialScale[0]],
        [0.35, UI_COLORS.sequentialScale[1]],
        [0.68, UI_COLORS.sequentialScale[2]],
        [1, UI_COLORS.sequentialScale[3]],
      ],
      sequentialminus: [
        [0, UI_COLORS.sequentialScale[0]],
        [0.35, UI_COLORS.sequentialScale[1]],
        [0.68, UI_COLORS.sequentialScale[2]],
        [1, UI_COLORS.sequentialScale[3]],
      ],
      diverging: [
        [0, UI_COLORS.divergingScale[0]],
        [0.5, UI_COLORS.divergingScale[1]],
        [1, UI_COLORS.divergingScale[2]],
      ],
    },
    font: {
      color: UI_COLORS.textMain,
      family: UI_COLORS.fontFamily,
    },
    title: {
      font: {
        color: UI_COLORS.textMain,
      },
    },
    legend: {
      bgcolor: UI_COLORS.panelElevated,
      bordercolor: UI_COLORS.border,
      borderwidth: 1,
      font: {
        color: UI_COLORS.textMain,
      },
      title: {
        font: {
          color: UI_COLORS.textMain,
        },
      },
    },
    hoverlabel: {
      bgcolor: UI_COLORS.chartTooltipBg,
      bordercolor: UI_COLORS.chartTooltipBorder,
      font: {
        color: UI_COLORS.textMain,
      },
    },
  }

  let themedLayout = mergeDeep(rawLayout, softLayoutPatch)
  themedLayout = applyAxisTheme(themedLayout, PLOTLY_THEME_MODE.SOFT, themedData)
  themedLayout = applyAnnotationTheme(themedLayout, PLOTLY_THEME_MODE.SOFT)
  if (mode === PLOTLY_THEME_MODE.HARD) {
    themedLayout = mergeDeep(themedLayout, {
      font: {
        family: UI_COLORS.fontFamily,
        size: 12,
      },
      title: {
        x: 0.02,
        xanchor: 'left',
        font: {
          family: UI_COLORS.fontFamily,
          size: 14,
        },
      },
      legend: {
        orientation: 'h',
        yanchor: 'bottom',
        y: 1.02,
        xanchor: 'right',
        x: 1,
        font: {
          family: UI_COLORS.fontFamily,
          size: 11,
        },
      },
      hoverlabel: {
        align: 'left',
        font: {
          family: UI_COLORS.fontFamily,
          size: 12,
        },
      },
      bargap: 0.2,
      bargroupgap: 0.08,
    })
    themedLayout.margin = mergeDeep(getHardMargins(context), themedLayout.margin)
    themedLayout = applyAxisTheme(themedLayout, PLOTLY_THEME_MODE.HARD, themedData)
    themedLayout = applyAnnotationTheme(themedLayout, PLOTLY_THEME_MODE.HARD)
    themedData = applyHardTraceDefaults(themedData)
  }
  themedLayout = stripUnusedColorAxis(themedLayout, themedData)

  return {
    ...figure,
    data: themedData,
    layout: themedLayout,
  }
}

export function applyPlotlyConfigTheme(
  config: unknown = {},
  options: { mode?: unknown } = {},
): RecordValue {
  const mode = normalizeMode(options.mode)
  const input = isPlainObject(config) ? config : {}
  const baseButtonsToRemove = ['pan2d', 'lasso2d', 'select2d']

  const themedConfig: RecordValue = {
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    ...input,
  }

  themedConfig.modeBarButtonsToRemove = uniqueStrings([
    ...baseButtonsToRemove,
    ...(Array.isArray(input.modeBarButtonsToRemove) ? input.modeBarButtonsToRemove : []),
  ])

  if (mode === PLOTLY_THEME_MODE.HARD) {
    themedConfig.toImageButtonOptions = mergeDeep(
      {
        format: 'png',
        width: 1400,
        height: 900,
        scale: 2,
      },
      input.toImageButtonOptions,
    )
  }

  return themedConfig
}
