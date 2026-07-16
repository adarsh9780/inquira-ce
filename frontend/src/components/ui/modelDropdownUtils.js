export function normalizeModelOption(option, fallbackProvider = '') {
  if (typeof option === 'string' || typeof option === 'number') {
    const value = String(option || '').trim()
    return {
      value,
      label: prettifyModelName(value),
      provider: providerFromValue(value) || String(fallbackProvider || '').trim(),
      tags: [],
    }
  }

  const raw = option && typeof option === 'object' ? option : {}
  const value = String(raw.value || raw.id || raw.model || '').trim()
  const label = String(raw.label || raw.name || raw.display_name || prettifyModelName(value)).trim() || prettifyModelName(value)
  const provider = String(raw.provider || providerFromValue(value) || fallbackProvider || '').trim()
  const tags = Array.isArray(raw.tags)
    ? raw.tags.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)
    : []

  return {
    ...raw,
    value,
    label,
    provider,
    tags,
  }
}

export function normalizeModelOptions(options, fallbackProvider = '') {
  const seen = new Set()
  const source = Array.isArray(options) ? options : []
  const normalized = []

  for (const option of source) {
    const item = normalizeModelOption(option, fallbackProvider)
    if (!item.value || seen.has(item.value)) continue
    seen.add(item.value)
    normalized.push(item)
  }

  return normalized
}

export function mergeModelOptions(primary, secondary = []) {
  return normalizeModelOptions([...(Array.isArray(primary) ? primary : []), ...(Array.isArray(secondary) ? secondary : [])])
}

export function optionMatchesSearch(option, query) {
  const normalized = String(query || '').trim().toLowerCase()
  if (!normalized) return true

  const fields = [
    option?.label,
    option?.value,
    option?.provider,
    providerLabel(option?.provider),
    Array.isArray(option?.tags) ? option.tags.join(' ') : '',
  ]
    .map((value) => String(value || '').toLowerCase())
    .filter(Boolean)

  return fields.some((field) => field.includes(normalized))
}

export function providerFromValue(value) {
  const raw = String(value || '').trim()
  if (!raw.includes('/')) return ''
  return raw.split('/')[0].trim()
}

export function providerLabel(provider) {
  const normalized = String(provider || '').trim().toLowerCase()
  if (!normalized || normalized === 'other') return 'Other'
  if (normalized === 'openai') return 'OpenAI'
  if (normalized === 'openrouter') return 'OpenRouter'
  if (normalized === 'anthropic') return 'Anthropic'
  if (normalized === 'google') return 'Google'
  if (normalized === 'ollama') return 'Ollama'
  return normalized
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}

export function prettifyModelName(modelId) {
  const raw = String(modelId || '').trim()
  if (!raw) return ''
  if (raw === 'openrouter/free') return 'OpenRouter Free'
  const withoutVendor = raw.includes('/') ? raw.split('/').slice(1).join('/') : raw
  return withoutVendor
    .split('-')
    .filter(Boolean)
    .map((part) => part.toUpperCase() === 'GPT' ? 'GPT' : `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}
