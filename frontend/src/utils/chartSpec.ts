export const CHART_SPEC_SCHEMA = 'inquira.chart/v1' as const

export type ChartMark = 'bar' | 'line' | 'area' | 'scatter' | 'pie' | 'donut' | 'heatmap' | 'histogram' | 'box' | 'violin'
export type ChartFieldType = 'quantitative' | 'nominal' | 'ordinal' | 'temporal'
export type ChartSort = 'ascending' | 'descending'

export interface ChartFieldEncoding {
  field: string
  type: ChartFieldType
  title?: string | null
  sort?: ChartSort | null
}

export interface ChartSpec {
  schema: typeof CHART_SPEC_SCHEMA
  data: { logical_name: string; artifact_id?: string | null }
  mark: ChartMark
  encoding: Partial<Record<'x' | 'y' | 'color' | 'size' | 'theta' | 'text', ChartFieldEncoding>>
  title: string
  description?: string | null
  options: {
    orientation: 'vertical' | 'horizontal'
    stacking: 'grouped' | 'stacked' | 'normalized'
    show_markers: boolean
  }
}

export class ChartSpecError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = 'ChartSpecError'
    this.code = code
  }
}

const MARKS = new Set<ChartMark>(['bar', 'line', 'area', 'scatter', 'pie', 'donut', 'heatmap', 'histogram', 'box', 'violin'])
const FIELD_TYPES = new Set<ChartFieldType>(['quantitative', 'nominal', 'ordinal', 'temporal'])
const CHANNELS = ['x', 'y', 'color', 'size', 'theta', 'text'] as const
const REQUIRED: Record<ChartMark, readonly string[]> = {
  bar: ['x', 'y'],
  line: ['x', 'y'],
  area: ['x', 'y'],
  scatter: ['x', 'y'],
  pie: ['theta', 'color'],
  donut: ['theta', 'color'],
  heatmap: ['x', 'y', 'color'],
  histogram: ['x'],
  box: ['x', 'y'],
  violin: ['x', 'y'],
}

function plainObject(value: unknown): Record<string, any> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, any>
}

function rejectUnknown(value: Record<string, any>, allowed: readonly string[], label: string) {
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key))
  if (unknown.length) throw new ChartSpecError('chart_spec_extra', `${label} contains unsupported field(s): ${unknown.join(', ')}`)
}

function requiredText(value: unknown, label: string, maxLength: number): string {
  const text = String(value || '').trim()
  if (!text) throw new ChartSpecError('chart_spec_required', `${label} is required.`)
  if (text.length > maxLength) throw new ChartSpecError('chart_spec_length', `${label} must be ${maxLength} characters or fewer.`)
  return text
}

export function parseChartSpec(value: unknown): ChartSpec {
  const source = plainObject(value)
  if (!source) throw new ChartSpecError('chart_spec_invalid', 'Chart spec must be a JSON object.')
  rejectUnknown(source, ['schema', 'data', 'mark', 'encoding', 'title', 'description', 'options'], 'Chart spec')
  if (source.schema !== CHART_SPEC_SCHEMA) throw new ChartSpecError('chart_schema_unsupported', `Chart schema must be ${CHART_SPEC_SCHEMA}.`)

  const data = plainObject(source.data)
  if (!data) throw new ChartSpecError('chart_data_invalid', 'Chart data must reference a dataframe artifact.')
  rejectUnknown(data, ['logical_name', 'artifact_id'], 'Chart data')
  const logicalName = requiredText(data.logical_name, 'Data logical name', 128)

  const mark = String(source.mark || '') as ChartMark
  if (!MARKS.has(mark)) throw new ChartSpecError('chart_mark_unsupported', `Unsupported chart mark: ${mark || 'missing'}.`)

  const rawEncoding = plainObject(source.encoding)
  if (!rawEncoding) throw new ChartSpecError('chart_encoding_invalid', 'Chart encoding must be an object.')
  rejectUnknown(rawEncoding, CHANNELS, 'Chart encoding')
  const encoding: ChartSpec['encoding'] = {}
  for (const channel of CHANNELS) {
    if (rawEncoding[channel] == null) continue
    const rawField = plainObject(rawEncoding[channel])
    if (!rawField) throw new ChartSpecError('chart_channel_invalid', `${channel} must be a field encoding.`)
    rejectUnknown(rawField, ['field', 'type', 'title', 'sort'], `${channel} encoding`)
    const type = String(rawField.type || '') as ChartFieldType
    if (!FIELD_TYPES.has(type)) throw new ChartSpecError('chart_field_type_invalid', `${channel} has an unsupported field type.`)
    const sort = rawField.sort == null ? null : String(rawField.sort) as ChartSort
    if (sort && sort !== 'ascending' && sort !== 'descending') throw new ChartSpecError('chart_sort_invalid', `${channel} has an unsupported sort direction.`)
    encoding[channel] = {
      field: requiredText(rawField.field, `${channel} field`, 256),
      type,
      title: rawField.title == null ? null : requiredText(rawField.title, `${channel} title`, 256),
      sort,
    }
  }
  const missing = REQUIRED[mark].filter((channel) => !encoding[channel as keyof typeof encoding])
  if (missing.length) throw new ChartSpecError('chart_channel_missing', `${mark} charts require: ${missing.join(', ')}.`)

  const rawOptions = source.options == null ? {} : plainObject(source.options)
  if (!rawOptions) throw new ChartSpecError('chart_options_invalid', 'Chart options must be an object.')
  rejectUnknown(rawOptions, ['orientation', 'stacking', 'show_markers'], 'Chart options')
  const orientation = String(rawOptions.orientation || 'vertical') as ChartSpec['options']['orientation']
  const stacking = String(rawOptions.stacking || 'grouped') as ChartSpec['options']['stacking']
  const showMarkers = rawOptions.show_markers == null ? true : rawOptions.show_markers
  if (!['vertical', 'horizontal'].includes(orientation)) throw new ChartSpecError('chart_orientation_invalid', 'Chart orientation must be vertical or horizontal.')
  if (!['grouped', 'stacked', 'normalized'].includes(stacking)) throw new ChartSpecError('chart_stacking_invalid', 'Chart stacking must be grouped, stacked, or normalized.')
  if (typeof showMarkers !== 'boolean') throw new ChartSpecError('chart_markers_invalid', 'show_markers must be true or false.')
  if ((mark === 'pie' || mark === 'donut') && orientation !== 'vertical') throw new ChartSpecError('chart_orientation_invalid', 'Pie and donut charts do not support horizontal orientation.')
  if (mark !== 'bar' && mark !== 'area' && stacking !== 'grouped') throw new ChartSpecError('chart_stacking_invalid', 'Stacking is only supported for bar and area charts.')

  return {
    schema: CHART_SPEC_SCHEMA,
    data: { logical_name: logicalName, artifact_id: data.artifact_id == null ? null : requiredText(data.artifact_id, 'Data artifact ID', 256) },
    mark,
    encoding,
    title: requiredText(source.title, 'Chart title', 256),
    description: source.description == null ? null : requiredText(source.description, 'Chart description', 1000),
    options: { orientation, stacking, show_markers: showMarkers },
  }
}

function field(spec: ChartSpec, channel: keyof ChartSpec['encoding']): string {
  const name = spec.encoding[channel]?.field
  if (!name) throw new ChartSpecError('chart_channel_missing', `Chart channel ${channel} is missing.`)
  return name
}

function validateRows(spec: ChartSpec, rows: Record<string, any>[]) {
  if (!rows.length) throw new ChartSpecError('chart_data_empty', 'The selected dataframe has no rows to chart.')
  const present = new Set(rows.flatMap((row) => Object.keys(row)))
  const missing = CHANNELS.flatMap((channel) => spec.encoding[channel]?.field || []).filter((name) => !present.has(name))
  if (missing.length) throw new ChartSpecError('chart_field_missing', `The dataframe does not contain chart field(s): ${[...new Set(missing)].join(', ')}.`)
}

function sortedRows(spec: ChartSpec, rows: Record<string, any>[]) {
  const encoding = spec.encoding.y?.sort ? spec.encoding.y : spec.encoding.x
  if (!encoding?.sort) return rows
  const direction = encoding.sort === 'descending' ? -1 : 1
  return [...rows].sort((left, right) => {
    const a = left[encoding.field]
    const b = right[encoding.field]
    if (a == null) return direction
    if (b == null) return -direction
    return direction * String(a).localeCompare(String(b), undefined, { numeric: true })
  })
}

function grouped(rows: Record<string, any>[], groupField?: string) {
  if (!groupField) return [[null, rows] as const]
  const groups = new Map<string, Record<string, any>[]>()
  for (const row of rows) {
    const key = String(row[groupField] ?? '')
    groups.set(key, [...(groups.get(key) || []), row])
  }
  return [...groups.entries()]
}

function axisTitle(encoding?: ChartFieldEncoding) {
  return encoding?.title || encoding?.field || null
}

export function compileChartSpec(value: unknown, records: unknown[]): Record<string, any> {
  const spec = parseChartSpec(value)
  const rows = records.filter((row): row is Record<string, any> => Boolean(plainObject(row))).map((row) => ({ ...row }))
  validateRows(spec, rows)
  const ordered = sortedRows(spec, rows)
  let traces: Record<string, any>[] = []

  if (['bar', 'line', 'area', 'scatter'].includes(spec.mark)) {
    const xField = field(spec, 'x')
    const yField = field(spec, 'y')
    const colorField = spec.encoding.color?.field
    traces = grouped(ordered, colorField).map(([name, groupRows]) => {
      const trace: Record<string, any> = {
        type: spec.mark === 'bar' ? 'bar' : 'scatter',
        x: groupRows.map((row) => row[xField]),
        y: groupRows.map((row) => row[yField]),
      }
      if (name != null) trace.name = name
      if (spec.mark === 'line') trace.mode = spec.options.show_markers ? 'lines+markers' : 'lines'
      if (spec.mark === 'area') {
        trace.mode = 'lines'
        if (spec.options.stacking === 'grouped') trace.fill = 'tozeroy'
        else trace.stackgroup = 'inquira'
        if (spec.options.stacking === 'normalized') trace.groupnorm = 'percent'
      }
      if (spec.mark === 'scatter') {
        trace.mode = 'markers'
        if (spec.encoding.size) trace.marker = { size: groupRows.map((row) => row[spec.encoding.size!.field]), sizemode: 'area' }
      }
      if (spec.mark === 'bar' && spec.options.orientation === 'horizontal') {
        ;[trace.x, trace.y] = [trace.y, trace.x]
        trace.orientation = 'h'
      }
      return trace
    })
  } else if (spec.mark === 'box' || spec.mark === 'violin') {
    const xField = field(spec, 'x')
    const yField = field(spec, 'y')
    traces = grouped(ordered, spec.encoding.color?.field).map(([name, groupRows]) => ({
      type: spec.mark,
      x: groupRows.map((row) => row[xField]),
      y: groupRows.map((row) => row[yField]),
      ...(spec.mark === 'box' ? { boxpoints: 'outliers' } : { points: 'outliers' }),
      ...(name == null ? {} : { name }),
    }))
  } else if (spec.mark === 'histogram') {
    const xField = field(spec, 'x')
    traces = [{ type: 'histogram', x: ordered.map((row) => row[xField]) }]
  } else if (spec.mark === 'pie' || spec.mark === 'donut') {
    traces = [{
      type: 'pie',
      labels: ordered.map((row) => row[field(spec, 'color')]),
      values: ordered.map((row) => row[field(spec, 'theta')]),
      hole: spec.mark === 'donut' ? 0.5 : 0,
    }]
  } else if (spec.mark === 'heatmap') {
    const xField = field(spec, 'x')
    const yField = field(spec, 'y')
    const colorField = field(spec, 'color')
    const x = [...new Set(ordered.map((row) => row[xField]))]
    const y = [...new Set(ordered.map((row) => row[yField]))]
    const cells = new Map<string, any>()
    for (const row of ordered) {
      const key = JSON.stringify([row[xField], row[yField]])
      if (cells.has(key)) throw new ChartSpecError('chart_heatmap_duplicate_cell', 'Heatmap data must have one row for each x/y combination.')
      cells.set(key, row[colorField])
    }
    traces = [{ type: 'heatmap', x, y, z: y.map((yv) => x.map((xv) => cells.get(JSON.stringify([xv, yv])))), colorbar: { title: axisTitle(spec.encoding.color) } }]
  }

  const horizontal = spec.mark === 'bar' && spec.options.orientation === 'horizontal'
  const layout: Record<string, any> = {
    title: { text: spec.title },
    xaxis: { title: { text: axisTitle(horizontal ? spec.encoding.y : spec.encoding.x) } },
    yaxis: { title: { text: axisTitle(horizontal ? spec.encoding.x : spec.encoding.y) } },
  }
  if (spec.mark === 'bar') {
    layout.barmode = spec.options.stacking === 'grouped' ? 'group' : 'stack'
    if (spec.options.stacking === 'normalized') layout.barnorm = 'percent'
  }
  return { data: traces, layout, config: { responsive: true, displaylogo: false } }
}
