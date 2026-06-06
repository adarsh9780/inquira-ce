export const WORKSPACE_LAYOUT_MODES = Object.freeze({
  VIEW: 'view',
  CHAT: 'chat',
  OUTPUT: 'output',
})

export const WORKSPACE_LAYOUT_ORDER = Object.freeze([
  WORKSPACE_LAYOUT_MODES.VIEW,
  WORKSPACE_LAYOUT_MODES.CHAT,
  WORKSPACE_LAYOUT_MODES.OUTPUT,
])

const LEGACY_LAYOUT_MODES = Object.freeze({
  split: WORKSPACE_LAYOUT_MODES.VIEW,
  data: WORKSPACE_LAYOUT_MODES.OUTPUT,
})

export function normalizeWorkspaceLayoutMode(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (WORKSPACE_LAYOUT_ORDER.includes(normalized)) return normalized
  return LEGACY_LAYOUT_MODES[normalized] || WORKSPACE_LAYOUT_MODES.VIEW
}

export function nextWorkspaceLayoutMode(value) {
  const current = normalizeWorkspaceLayoutMode(value)
  const index = WORKSPACE_LAYOUT_ORDER.indexOf(current)
  return WORKSPACE_LAYOUT_ORDER[(index + 1) % WORKSPACE_LAYOUT_ORDER.length]
}

export function workspaceLayoutVisibility(value) {
  const mode = normalizeWorkspaceLayoutMode(value)
  return {
    showSidebar: mode === WORKSPACE_LAYOUT_MODES.VIEW,
    showLeftPane: mode !== WORKSPACE_LAYOUT_MODES.OUTPUT,
    showRightPane: mode !== WORKSPACE_LAYOUT_MODES.CHAT,
  }
}

export function resolveWorkspaceLayoutShortcut(event) {
  if (!event || !(event.metaKey || event.ctrlKey) || !event.altKey || event.shiftKey) return ''
  const code = String(event.code || '')
  if (code === 'KeyV') return WORKSPACE_LAYOUT_MODES.VIEW
  if (code === 'KeyC') return WORKSPACE_LAYOUT_MODES.CHAT
  if (code === 'KeyO') return WORKSPACE_LAYOUT_MODES.OUTPUT
  return ''
}
