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
  const termsSource = read('src/components/modals/TermsModal.vue')

  assert.equal(settingsSource.includes('<DialogShell'), true)
  assert.equal(settingsSource.includes(':global('), false)

  assert.equal(termsSource.includes('<DialogShell'), true)
  assert.equal(termsSource.includes('bg-white'), false)
  assert.equal(termsSource.includes('text-gray-'), false)
})

test('dropdown, toast, and blocking overlays use layer utility classes', () => {
  const headerDropdown = read('src/components/ui/HeaderDropdown.vue')
  const sharedDropdown = read('src/components/ui/dropdownShared.ts')
  const toastContainer = read('src/components/ui/ToastContainer.vue')
  const appSource = read('src/components/startup/BlockingOperationOverlay.vue')

  assert.equal(headerDropdown.includes('dropdownSurfaceClass'), true)
  assert.equal(sharedDropdown.includes("layer-modal-dropdown fixed"), true)
  assert.equal(toastContainer.includes('class="layer-toast fixed'), true)

  assert.equal(appSource.includes('class="layer-blocking fixed inset-0'), true)
  assert.equal(appSource.includes('z-[9999]'), false)
})
