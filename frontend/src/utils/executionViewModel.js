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

export function buildExecutionViewModel(response, options = {}) {
  const opts = {
    dataframeLine: (count) => `✅ ${count} dataframe(s) found. Available in Table tab.`,
    figureLine: (count) => `✅ ${count} figure(s) found. Available in Chart tab.`,
    scalarLine: (count) => `✅ ${count} scalar(s) found. Available in Terminal tab.`,
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

  if (parsedDataframes.entries.length > 0) {
    outputParts.push(opts.dataframeLine(parsedDataframes.entries.length))
  }
  if (parsedDataframes.failed > 0) {
    outputParts.push(opts.dataframeParseErrorLine)
  }

  if (parsedFigures.entries.length > 0) {
    outputParts.push(opts.figureLine(parsedFigures.entries.length))
  }
  if (parsedFigures.failed > 0) {
    outputParts.push(opts.figureParseErrorLine)
  }

  if (parsedScalars.entries.length > 0) {
    outputParts.push(opts.scalarLine(parsedScalars.entries.length))
  }
  if (parsedScalars.failed > 0) {
    outputParts.push(opts.scalarParseErrorLine)
  }

  if (opts.includeVariableSummary) {
    outputParts.push(
      opts.variableSummaryLine({
        dataframes: parsedDataframes.rawCount,
        figures: parsedFigures.rawCount,
        scalars: parsedScalars.rawCount,
      }),
    )
  }

  if (!response?.error && opts.successLine) {
    outputParts.push(opts.successLine)
  }

  return {
    output: outputParts.join('\n\n'),
    dataframes: parsedDataframes.entries.map(({ name, value }) => ({ name, data: value })),
    figures: parsedFigures.entries.map(({ name, value }) => ({ name, data: value })),
    scalars: parsedScalars.entries.map(({ name, value }) => ({ name, value })),
    counts: {
      dataframes: parsedDataframes.rawCount,
      figures: parsedFigures.rawCount,
      scalars: parsedScalars.rawCount,
    },
  }
}

