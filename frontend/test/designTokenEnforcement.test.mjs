import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

function walkVueFiles(dir) {
  const files = []
  for (const entry of readdirSync(dir)) {
    const fullPath = resolve(dir, entry)
    const stats = statSync(fullPath)
    if (stats.isDirectory()) {
      files.push(...walkVueFiles(fullPath))
      continue
    }
    if (fullPath.endsWith('.vue')) files.push(fullPath)
  }
  return files
}

test('design tokens define motion, blur, overlay, and semantic color primitives', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--motion-duration-standard:'), true)
  assert.equal(source.includes('--motion-ease-standard:'), true)
  assert.equal(source.includes('--blur-backdrop-modal:'), true)
  assert.equal(source.includes('--overlay-backdrop-color:'), true)
  assert.equal(source.includes('--overlay-backdrop-strong:'), true)
  assert.equal(source.includes('--shadow-modal:'), true)
  assert.equal(source.includes('.modal-overlay {'), true)
  assert.equal(source.includes('.modal-overlay-strong {'), true)
  assert.equal(source.includes('.dialog-fade-enter-active,'), true)
  assert.equal(source.includes('.dialog-pop-enter-active,'), true)
  assert.equal(source.includes('.motion-fast {'), true)
  assert.equal(source.includes('.motion-standard {'), true)
  assert.equal(source.includes('.motion-slow {'), true)
})

test('component styles avoid hardcoded hex/rgba colors outside approved brand icon SVG', () => {
  const componentRoot = resolve(process.cwd(), 'src/components')
  const files = walkVueFiles(componentRoot)
  const hexPattern = /#[0-9a-fA-F]{3,8}\b/g
  const rgbaPattern = /rgba?\(/g

  const allowedHexFileSuffixes = new Set([
    resolve(componentRoot, 'modals/tabs/AccountTab.vue'),
  ])

  for (const filePath of files) {
    const source = readFileSync(filePath, 'utf-8')
    if (!allowedHexFileSuffixes.has(filePath)) {
      const hexMatches = source.match(hexPattern) || []
      assert.equal(
        hexMatches.length,
        0,
        `Hardcoded hex color in ${filePath}: ${hexMatches.slice(0, 3).join(', ')}`,
      )
    }

    const rgbaMatches = source.match(rgbaPattern) || []
    assert.equal(
      rgbaMatches.length,
      0,
      `Hardcoded rgba()/rgb() color in ${filePath}: ${rgbaMatches.slice(0, 3).join(', ')}`,
    )
  }
})

test('modal surfaces use shared tokenized dialog transition primitives', () => {
  const settingsModal = readFileSync(resolve(process.cwd(), 'src/components/modals/SettingsModal.vue'), 'utf-8')
  const confirmationModal = readFileSync(resolve(process.cwd(), 'src/components/modals/ConfirmationModal.vue'), 'utf-8')
  const renameModal = readFileSync(resolve(process.cwd(), 'src/components/modals/WorkspaceRenameModal.vue'), 'utf-8')
  const progressModal = readFileSync(resolve(process.cwd(), 'src/components/modals/SettingsProgressModal.vue'), 'utf-8')

  for (const source of [settingsModal, confirmationModal, renameModal, progressModal]) {
    assert.equal(source.includes('dialog-fade-enter-active'), true)
    assert.equal(source.includes('dialog-pop-enter-active'), true)
    assert.match(source, /class="[^"]*\bmodal-overlay\b[^"]*"/)
    assert.match(source, /class="[^"]*\bmodal-card\b[^"]*"/)
  }
})
