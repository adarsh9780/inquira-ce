import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('heavy workbench features are behind explicit async boundaries', () => {
  const app = read('../src/App.vue')
  const workPane = read('../src/components/layout/WorkspaceLeftPane.vue')
  const rightPanel = read('../src/components/layout/RightPanel.vue')
  const settings = read('../src/components/modals/SettingsModal.vue')
  const plotlyLoader = read('../src/utils/loadPlotly.ts')
  const chatHistory = read('../src/components/chat/ChatHistory.vue')
  const toolActivity = read('../src/components/chat/ToolActivityCard.vue')

  assert.match(app, /defineAsyncComponent\(\(\) => import\('\.\/components\/modals\/SettingsModal\.vue'\)\)/)
  assert.match(workPane, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/CodeTab\.vue'\)\)/)
  assert.match(rightPanel, /defineAsyncComponent\(\(\) => import\('\.\.\/analysis\/TerminalTab\.vue'\)\)/)
  assert.match(settings, /defineAsyncComponent\(\(\) => import\('\.\/tabs\/WorkspaceTab\.vue'\)\)/)
  assert.match(plotlyLoader, /import\('plotly\.js-dist-min'\)/)
  assert.match(chatHistory, /defineAsyncComponent\(\(\) => import\('\.\/MarkdownContent\.vue'\)\)/)
  assert.match(toolActivity, /defineAsyncComponent\(\(\) => import\('\.\/ToolOutputPreview\.vue'\)\)/)
})

test('the application root composes dedicated startup and shell components', () => {
  const app = read('../src/App.vue')
  for (const component of ['StartupScreen', 'StartupFailureScreen', 'BlockingOperationOverlay', 'AppShell']) {
    assert.match(app, new RegExp(`<${component}`))
  }
})
