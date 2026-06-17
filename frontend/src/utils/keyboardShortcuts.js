export const SHORTCUTS = [
  { id: 'conversation-tree', category: 'Navigation', label: 'Open Conversation Tree', keys: ['mod', 't'], title: 'Conversation Tree' },
  { id: 'schema', category: 'Navigation', label: 'Open Schema', keys: ['mod', 's'], title: 'Schema' },
  { id: 'keyboard-shortcuts', category: 'Navigation', label: 'Open Keyboard Shortcuts', keys: ['mod', 'k'], title: 'Keyboard Shortcuts' },
  { id: 'dataset-import', category: 'Data', label: 'Import Dataset', keys: ['mod', 'o'], title: 'Import Dataset' },
  { id: 'sidebar', category: 'Workspace', label: 'Toggle Sidebar', keys: ['mod', 'b'], title: 'Sidebar' },
  { id: 'terminal', category: 'Workspace', label: 'Toggle Terminal', keys: ['mod', 'j'], title: 'Terminal' },
  { id: 'layout-cycle', category: 'Layout', label: 'Cycle Workspace Layout', keys: ['mod', 'shift', 'd'], title: 'Cycle Layout' },
  { id: 'layout-view', category: 'Layout', label: 'View Layout', keys: ['mod', 'alt', 'v'], title: 'View Layout' },
  { id: 'layout-chat', category: 'Layout', label: 'Chat Layout', keys: ['mod', 'alt', 'c'], title: 'Chat Layout' },
  { id: 'layout-output', category: 'Layout', label: 'Output Layout', keys: ['mod', 'alt', 'o'], title: 'Output Layout' },
]

export function shortcutLabel(shortcut, platform = '') {
  const isMac = String(platform || '').toLowerCase().includes('mac')
  return (shortcut?.keys || []).map((key) => {
    if (key === 'mod') return isMac ? 'Cmd' : 'Ctrl'
    if (key === 'alt') return isMac ? 'Option' : 'Alt'
    if (key === 'shift') return 'Shift'
    return String(key || '').toUpperCase()
  }).join('+')
}

export function shortcutTitle(shortcutId, fallback = '', platform = '') {
  const shortcut = SHORTCUTS.find((item) => item.id === shortcutId)
  if (!shortcut) return fallback
  const label = shortcutLabel(shortcut, platform)
  return `${fallback || shortcut.title || shortcut.label} (${label})`
}

export function matchShortcut(event, shortcutId) {
  const shortcut = SHORTCUTS.find((item) => item.id === shortcutId)
  if (!event || !shortcut) return false
  const keys = shortcut.keys || []
  const wantsMod = keys.includes('mod')
  const wantsAlt = keys.includes('alt')
  const wantsShift = keys.includes('shift')
  const key = String(event.key || '').toLowerCase()
  const characterKey = keys.find((item) => !['mod', 'alt', 'shift'].includes(item))
  return (
    (!wantsMod || event.metaKey || event.ctrlKey)
    && Boolean(event.altKey) === wantsAlt
    && Boolean(event.shiftKey) === wantsShift
    && key === characterKey
  )
}

export function shortcutsByCategory() {
  return SHORTCUTS.reduce((groups, shortcut) => {
    const category = shortcut.category || 'General'
    if (!groups[category]) groups[category] = []
    groups[category].push(shortcut)
    return groups
  }, {})
}

