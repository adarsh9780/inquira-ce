export interface Shortcut {
  id: string
  category: string
  label: string
  keys: string[]
  title: string
}

type ShortcutEvent = Pick<KeyboardEvent, 'altKey' | 'ctrlKey' | 'key' | 'metaKey' | 'shiftKey'>

export const SHORTCUTS: Shortcut[] = [
  { id: 'conversation-tree', category: 'Navigation', label: 'Open Conversation Tree', keys: ['mod', 't'], title: 'Conversation Tree' },
  { id: 'schema', category: 'Navigation', label: 'Open Schema', keys: ['mod', 's'], title: 'Schema' },
  { id: 'settings', category: 'Navigation', label: 'Open Settings', keys: ['mod', ','], title: 'Settings' },
  { id: 'dataset-import', category: 'Data', label: 'Import Dataset', keys: ['mod', 'o'], title: 'Import Dataset' },
  { id: 'conversation-switcher', category: 'Workspace', label: 'Search Conversations', keys: ['mod', 'k'], title: 'Conversations' },
  { id: 'sidebar', category: 'Workspace', label: 'Toggle Sidebar', keys: ['mod', 'b'], title: 'Sidebar' },
  { id: 'terminal', category: 'Workspace', label: 'Toggle Terminal', keys: ['mod', 'j'], title: 'Terminal' },
]

export function shortcutLabel(shortcut: Shortcut | null | undefined, platform = ''): string {
  const isMac = String(platform || '').toLowerCase().includes('mac')
  return (shortcut?.keys || []).map((key) => {
    if (key === 'mod') return isMac ? 'Cmd' : 'Ctrl'
    if (key === 'alt') return isMac ? 'Option' : 'Alt'
    if (key === 'shift') return 'Shift'
    return String(key || '').toUpperCase()
  }).join('+')
}

export function shortcutTitle(shortcutId: string, fallback = '', platform = ''): string {
  const shortcut = SHORTCUTS.find((item) => item.id === shortcutId)
  if (!shortcut) return fallback
  const label = shortcutLabel(shortcut, platform)
  return `${fallback || shortcut.title || shortcut.label} (${label})`
}

export function matchShortcut(
  event: ShortcutEvent | null | undefined,
  shortcutId: string,
): boolean {
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

export function shortcutsByCategory(): Record<string, Shortcut[]> {
  return SHORTCUTS.reduce<Record<string, Shortcut[]>>((groups, shortcut) => {
    const category = shortcut.category || 'General'
    if (!groups[category]) groups[category] = []
    groups[category].push(shortcut)
    return groups
  }, {})
}
