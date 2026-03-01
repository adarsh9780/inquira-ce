import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('right panel only shows terminal tab when terminal feature flag is enabled', () => {
  const rightPanelPath = resolve(process.cwd(), 'src/components/layout/RightPanel.vue')
  const source = readFileSync(rightPanelPath, 'utf-8')

  assert.equal(source.includes('...(appStore.terminalEnabled ? [{'), true)
  assert.equal(source.includes("id: 'terminal'"), true)
})
