import { describe, expect, it } from 'vitest'

import {
  matchShortcut,
  shortcutLabel,
  shortcutsByCategory,
  SHORTCUTS,
} from '../src/utils/keyboardShortcuts'

describe('keyboard shortcuts', () => {
  it('renders platform-specific modifier labels', () => {
    const conversationSwitcher = SHORTCUTS.find((shortcut) => shortcut.id === 'conversation-switcher')

    expect(shortcutLabel(conversationSwitcher, 'MacIntel')).toBe('Cmd+K')
    expect(shortcutLabel(conversationSwitcher, 'Win32')).toBe('Ctrl+K')
  })

  it('matches the required modifiers and character key', () => {
    expect(matchShortcut(
      { key: 'k', metaKey: true, ctrlKey: false, altKey: false, shiftKey: false },
      'conversation-switcher',
    )).toBe(true)
    expect(matchShortcut(
      { key: 'k', metaKey: false, ctrlKey: false, altKey: false, shiftKey: false },
      'conversation-switcher',
    )).toBe(false)
  })

  it('groups shortcuts by their declared category', () => {
    expect(shortcutsByCategory().Navigation.map((shortcut) => shortcut.id)).toContain('schema')
  })
})
