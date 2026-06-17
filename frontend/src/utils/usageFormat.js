const USAGE_FIELDS = ['input_tokens', 'output_tokens', 'cached_tokens', 'total_tokens', 'price_usd']

export function toProvidedUsageNumber(value) {
  if (value === null || value === undefined || typeof value === 'boolean') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null
}

export function normalizeUsage(value) {
  if (!value || typeof value !== 'object') return null
  const normalized = {}
  let hasValue = false
  for (const field of USAGE_FIELDS) {
    const parsed = toProvidedUsageNumber(value[field])
    normalized[field] = parsed
    if (parsed !== null) hasValue = true
  }
  return hasValue ? normalized : null
}

export function emptyUsage() {
  return {
    input_tokens: null,
    output_tokens: null,
    cached_tokens: null,
    total_tokens: null,
    price_usd: null,
  }
}

export function mergeUsageTotals(base, incoming) {
  const left = normalizeUsage(base) || emptyUsage()
  const right = normalizeUsage(incoming)
  if (!right) return normalizeUsage(left)
  const merged = emptyUsage()
  for (const field of USAGE_FIELDS) {
    const leftValue = left[field]
    const rightValue = right[field]
    if (leftValue === null && rightValue === null) merged[field] = null
    else merged[field] = (leftValue || 0) + (rightValue || 0)
  }
  return normalizeUsage(merged)
}

export function formatTokenCount(value) {
  const parsed = toProvidedUsageNumber(value)
  if (parsed === null) return '-'
  const whole = Math.round(parsed)
  if (whole >= 1000000) return `${(whole / 1000000).toFixed(1).replace(/\.0$/, '')}m`
  if (whole >= 1000) return `${(whole / 1000).toFixed(1).replace(/\.0$/, '')}k`
  return String(whole)
}

export function formatUsd(value) {
  const parsed = toProvidedUsageNumber(value)
  if (parsed === null) return '-'
  return `$${parsed.toFixed(6)}`
}

export function formatUsageCompact(value) {
  const usage = normalizeUsage(value) || emptyUsage()
  return `In ${formatTokenCount(usage.input_tokens)} | Out ${formatTokenCount(usage.output_tokens)} | Cost ${formatUsd(usage.price_usd)}`
}

export function formatUsageTooltip(value, summary = null) {
  const usage = normalizeUsage(value) || emptyUsage()
  const lines = [
    `Input tokens: ${formatTokenCount(usage.input_tokens)}`,
    `Cached input tokens: ${formatTokenCount(usage.cached_tokens)}`,
    `Output tokens: ${formatTokenCount(usage.output_tokens)}`,
    `Total tokens: ${formatTokenCount(usage.total_tokens)}`,
    usage.price_usd === null ? 'Cost unavailable' : `Cost (USD): ${formatUsd(usage.price_usd)}`,
  ]
  const turnCount = Number(summary?.turn_count)
  const turnsWithUsage = Number(summary?.turns_with_usage)
  if (Number.isFinite(turnCount)) lines.push(`Turns: ${turnCount}`)
  if (Number.isFinite(turnsWithUsage)) lines.push(`Turns with usage: ${turnsWithUsage}`)
  return lines.join('\n')
}

