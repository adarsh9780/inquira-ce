import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('right panel resizer uses container bounds instead of hardcoded body/sidebar math', () => {
  const panelPath = resolve(process.cwd(), 'src/components/layout/RightPanel.vue')
  const source = readFileSync(panelPath, 'utf-8')

  assert.equal(source.includes('ref="panelRef"'), true)
  assert.equal(source.includes('getBoundingClientRect'), true)
  assert.equal(source.includes('document.body.clientWidth - (appStore.isSidebarCollapsed ? 64 : 256)'), false)
  assert.equal(source.includes('document.body.clientHeight'), false)
})
