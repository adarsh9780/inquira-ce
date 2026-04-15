import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('theme declares shared settings aliases and z-layer scale', () => {
  const source = read('src/style.css')

  assert.equal(source.includes('--color-text-sub:'), true)
  assert.equal(source.includes('--color-base-soft:'), true)
  assert.equal(source.includes('--color-border-strong:'), true)
  assert.equal(source.includes('--color-base-muted:'), true)
  assert.equal(source.includes('--color-danger:'), true)
  assert.equal(source.includes('--color-info:'), true)
  assert.equal(source.includes('--color-success-bg:'), true)
  assert.equal(source.includes('--color-surface-subtle:'), true)
  assert.equal(source.includes('--z-dropdown:'), true)
  assert.equal(source.includes('--z-modal:'), true)
  assert.equal(source.includes('--z-modal-dropdown:'), true)
  assert.equal(source.includes('--z-toast:'), true)
  assert.equal(source.includes('--z-blocking:'), true)
  assert.equal(source.includes('.layer-dropdown'), true)
  assert.equal(source.includes('.layer-modal'), true)
  assert.equal(source.includes('.layer-modal-dropdown'), true)
  assert.equal(source.includes('.layer-toast'), true)
  assert.equal(source.includes('.layer-blocking'), true)
})

test('settings-related modals use shared modal primitives and avoid scoped global leakage', () => {
  const settingsSource = read('src/components/modals/SettingsModal.vue')
  const historySource = read('src/components/chat/ConversationHistoryModal.vue')
  const progressSource = read('src/components/modals/SettingsProgressModal.vue')

  assert.equal(settingsSource.includes('class="fixed inset-0 layer-modal'), true)
  assert.equal(settingsSource.includes('class="modal-overlay"'), true)
  assert.equal(settingsSource.includes('class="modal-card'), true)
  assert.equal(settingsSource.includes(':global('), false)

  assert.equal(historySource.includes('class="fixed inset-0 layer-modal'), true)
  assert.equal(historySource.includes('class="modal-overlay"'), true)
  assert.equal(historySource.includes('class="modal-card'), true)
  assert.equal(historySource.includes('bg-white'), false)
  assert.equal(historySource.includes('text-gray-'), false)

  assert.equal(progressSource.includes('class="fixed inset-0 layer-modal'), true)
  assert.equal(progressSource.includes('class="modal-overlay"'), true)
  assert.equal(progressSource.includes('class="modal-card'), true)
  assert.equal(progressSource.includes('bg-white'), false)
  assert.equal(progressSource.includes('text-gray-'), false)
})

test('dropdown, toast, and blocking overlays use layer utility classes', () => {
  const headerDropdown = read('src/components/ui/HeaderDropdown.vue')
  const multiSelectDropdown = read('src/components/ui/MultiSelectDropdown.vue')
  const toastContainer = read('src/components/ui/ToastContainer.vue')
  const dataTab = read('src/components/modals/DataTab.vue')
  const appSource = read('src/App.vue')

  assert.equal(headerDropdown.includes('class="layer-modal-dropdown fixed'), true)
  assert.equal(multiSelectDropdown.includes('class="layer-modal-dropdown fixed'), true)
  assert.equal(toastContainer.includes('class="layer-toast fixed'), true)

  assert.equal(dataTab.includes('class="layer-blocking fixed inset-0'), true)
  assert.equal(dataTab.includes('z-[9999]'), false)
  assert.equal(appSource.includes('class="layer-blocking fixed inset-0'), true)
  assert.equal(appSource.includes('z-[9999]'), false)
})
