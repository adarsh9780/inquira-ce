import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar layout button toggles the data pane directly', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('@click="appStore.toggleDataPaneVisibility()"'), true)
  assert.equal(source.includes('@click="appStore.cycleWorkspaceLayoutMode()"'), false)
  assert.equal(source.includes("return 'Show data pane'"), true)
  assert.equal(source.includes("return 'Hide data pane'"), true)
})
