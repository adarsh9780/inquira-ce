import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('command palette is app-level and uses Cmd/Ctrl+B for conversation switching', () => {
  const app = read('src/App.vue')
  const store = read('src/stores/appStore.js')
  const shortcuts = read('src/utils/keyboardShortcuts.js')
  const modal = read('src/components/modals/CommandPaletteModal.vue')
  const leftPane = read('src/components/layout/WorkspaceLeftPane.vue')

  assert.equal(shortcuts.includes("id: 'command-palette'"), true)
  assert.equal(shortcuts.includes("keys: ['mod', 'b']"), true)
  assert.equal(app.includes('CommandPaletteModal'), true)
  assert.equal(app.includes("matchShortcut(event, 'command-palette')"), true)
  assert.equal(app.includes('appStore.toggleCommandPalette()'), true)
  assert.equal(store.includes('const isCommandPaletteOpen = ref(false)'), true)
  assert.equal(store.includes('function openCommandPalette()'), true)
  assert.equal(store.includes('function closeCommandPalette()'), true)
  assert.equal(store.includes('function toggleCommandPalette()'), true)
  assert.equal(leftPane.includes('appStore.openCommandPalette()'), true)
  assert.equal(leftPane.includes('MagnifyingGlassIcon'), true)
  assert.equal(leftPane.includes('CommandLineIcon'), false)
  assert.equal(modal.includes('Command Palette'), true)
  assert.equal(modal.includes('MagnifyingGlassIcon'), true)
  assert.equal(modal.includes('CommandLineIcon'), false)
  assert.equal(modal.includes('apiService.v1ListConversations(workspaceId, 200)'), true)
  assert.equal(modal.includes('appStore.isConversationRunning(id)'), true)
  assert.equal(modal.includes('formatCreatedLabel(createdAt)'), true)
  assert.equal(modal.includes('workspaceInitials(row.workspaceName)'), true)
  assert.equal(modal.includes('appStore.activateWorkspace(row.workspaceId)'), true)
  assert.equal(modal.includes('appStore.fetchConversationTurns({ reset: true, preferLatest: true })'), true)
})
