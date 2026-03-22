import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace-driven panels guard backend calls until active workspace is valid', () => {
  const statusBar = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )
  const tableTab = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )
  const figureTab = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )
  const terminalTab = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue'),
    'utf-8',
  )
  const apiService = readFileSync(
    resolve(process.cwd(), 'src/services/apiService.js'),
    'utf-8',
  )

  assert.equal(statusBar.includes('if (!appStore.activeWorkspaceId || !appStore.hasWorkspace || isKernelActionRunning.value) return'), true)
  assert.equal(tableTab.includes('if (!appStore.activeWorkspaceId || !appStore.hasWorkspace) return'), true)
  assert.equal(tableTab.includes('if (!normalizedWorkspaceId || !appStore.hasWorkspace)'), true)
  assert.equal(figureTab.includes('if (!normalizedWorkspaceId || !appStore.hasWorkspace)'), true)
  assert.equal(terminalTab.includes('if (!appStore.activeWorkspaceId || !appStore.hasWorkspace)'), true)
  assert.equal(apiService.includes('if (!appStore.activeWorkspaceId) {'), true)
  assert.equal(apiService.includes('if (!appStore.activeWorkspaceId || !appStore.hasWorkspace) {'), true)
})
