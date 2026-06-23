export function updateFloatingDropdownPosition(triggerRef, {
  minHeight = 180,
  maxHeight = 320,
  spacing = 6,
  minSpace = 120,
  surface = 'var(--color-surface)',
  border = 'var(--color-border)',
} = {}) {
  const triggerEl = triggerRef?.value?.el ?? triggerRef?.value ?? triggerRef
  if (!triggerEl?.getBoundingClientRect) return null

  const rect = triggerEl.getBoundingClientRect()
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0
  const spaceBelow = Math.max(viewportHeight - rect.bottom - spacing, minSpace)
  const spaceAbove = Math.max(rect.top - spacing, minSpace)
  const openUpward = spaceBelow < minHeight && spaceAbove > spaceBelow
  const style = {
    left: `${Math.round(rect.left)}px`,
    width: `${Math.round(rect.width)}px`,
    maxHeight: `${Math.round(Math.min(maxHeight, openUpward ? spaceAbove : spaceBelow))}px`,
    backgroundColor: surface,
    border: `1px solid ${border}`,
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
