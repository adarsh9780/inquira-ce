interface FloatingDropdownOptions {
  minHeight?: number
  maxHeight?: number
  spacing?: number
  minSpace?: number
  surface?: string
  border?: string
}

export interface FloatingDropdownStyle extends Record<string, string> {
  left: string
  width: string
  maxHeight: string
  backgroundColor: string
  border: string
  '--motion-popover-origin': string
  '--motion-popover-y': string
  top: string
  bottom: string
}

type TriggerElement = Pick<HTMLElement, 'getBoundingClientRect'>

function isTriggerElement(value: unknown): value is TriggerElement {
  return Boolean(
    value
    && typeof value === 'object'
    && typeof (value as { getBoundingClientRect?: unknown }).getBoundingClientRect === 'function',
  )
}

function resolveTriggerElement(source: unknown): TriggerElement | null {
  if (isTriggerElement(source)) return source
  if (!source || typeof source !== 'object') return null
  const record = source as { value?: unknown; el?: unknown }
  if (isTriggerElement(record.el)) return record.el
  if (isTriggerElement(record.value)) return record.value
  if (record.value && typeof record.value === 'object') {
    const wrapped = record.value as { el?: unknown }
    if (isTriggerElement(wrapped.el)) return wrapped.el
  }
  return null
}

export function updateFloatingDropdownPosition(triggerRef: unknown, {
  minHeight = 180,
  maxHeight = 320,
  spacing = 6,
  minSpace = 120,
  surface = 'var(--color-surface)',
  border = 'var(--color-border)',
}: FloatingDropdownOptions = {}): FloatingDropdownStyle | null {
  const triggerEl = resolveTriggerElement(triggerRef)
  if (!triggerEl) return null

  const rect = triggerEl.getBoundingClientRect()
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0
  const spaceBelow = Math.max(viewportHeight - rect.bottom - spacing, minSpace)
  const spaceAbove = Math.max(rect.top - spacing, minSpace)
  const openUpward = spaceBelow < minHeight && spaceAbove > spaceBelow
  const style: FloatingDropdownStyle = {
    left: `${Math.round(rect.left)}px`,
    width: `${Math.round(rect.width)}px`,
    maxHeight: `${Math.round(Math.min(maxHeight, openUpward ? spaceAbove : spaceBelow))}px`,
    backgroundColor: surface,
    border: `1px solid ${border}`,
    '--motion-popover-origin': openUpward ? 'bottom center' : 'top center',
    '--motion-popover-y': openUpward ? 'var(--motion-distance-popover)' : 'calc(var(--motion-distance-popover) * -1)',
    top: 'auto',
    bottom: 'auto',
  }

  if (openUpward) {
    style.bottom = `${Math.max(Math.round(viewportHeight - rect.top + spacing), spacing)}px`
    style.top = 'auto'
  } else {
    style.top = `${Math.round(rect.bottom + spacing)}px`
    style.bottom = 'auto'
  }

  return style
}
