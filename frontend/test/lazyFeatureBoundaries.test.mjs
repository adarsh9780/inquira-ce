import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('settings and app-level utility dialogs load only when opened', () => {
  const app = read('src/App.vue')

  assert.match(app, /defineAsyncComponent\(\(\) => import\('\.\/components\/modals\/SettingsModal\.vue'\)\)/)
  assert.match(app, /defineAsyncComponent\(\(\) => import\('\.\/components\/modals\/CommandPaletteModal\.vue'\)\)/)
  assert.match(app, /defineAsyncComponent\(\(\) => import\('\.\/components\/modals\/KeyboardShortcutsModal\.vue'\)\)/)
  assert.match(app, /<SettingsModal\s+v-if="uiStore\.isSettingsOpen"/)
  assert.match(app, /<CommandPaletteModal\s+v-if="uiStore\.isCommandPaletteOpen"/)
})

test('CodeMirror, terminal, schema, and tree feature roots are async and mount on demand', () => {
  const leftPane = read('src/components/layout/WorkspaceLeftPane.vue')
  const rightPanel = read('src/components/layout/RightPanel.vue')

  assert.match(leftPane, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/CodeTab\.vue'\)\)/)
  assert.match(leftPane, /v-if="appStore\.workspacePane === 'code'"/)
  assert.match(rightPanel, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/TerminalTab\.vue'\)\)/)
  assert.match(rightPanel, /defineAsyncComponent\(\(\) => import\('\.\.\/preview\/SchemaEditorTab\.vue'\)\)/)
  assert.match(rightPanel, /defineAsyncComponent\(\(\) => import\('\.\/sidebar\/SidebarGlobalTurnTree\.vue'\)\)/)
  assert.match(rightPanel, /<TerminalTab v-if="appStore\.isTerminalOpen"/)
})

test('table, figure, output, and nested chart renderers remain async', () => {
  const rightPane = read('src/components/layout/WorkspaceRightPane.vue')
  const output = read('src/components/analysis/OutputTab.vue')

  assert.match(rightPane, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/TableTab\.vue'\)\)/)
  assert.match(rightPane, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/FigureTab\.vue'\)\)/)
  assert.match(rightPane, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/OutputTab\.vue'\)\)/)
  assert.match(output, /defineAsyncComponent\(\(\) => import\('\.\/runs\/RunChartOutput\.vue'\)\)/)
})
