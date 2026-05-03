import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('layout defines elevated light surfaces for sidebar and active workspace panes', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(styleSource.includes('--color-shell-backdrop: #F5F4EF;'), true)
  assert.equal(styleSource.includes('--color-sidebar-surface: #EFEDE8;'), true)
  assert.equal(styleSource.includes('--color-workspace-surface: #FAF9F6;'), true)
  assert.equal(appSource.includes('class="flex-1 flex overflow-hidden app-shell-frame relative"'), true)
  assert.equal(appSource.includes('class="h-full shrink-0 app-nav-pane"'), true)
  assert.equal(appSource.includes(":class=\"{ 'app-nav-pane-collapsed': appStore.isSidebarCollapsed }\""), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(appSource.includes('class="flex-1 flex flex-col overflow-hidden app-workspace-pane"'), true)
  assert.equal(appSource.includes('.app-nav-pane {'), true)
  assert.equal(appSource.includes('.app-workspace-pane {'), true)
  assert.equal(appSource.includes('background-color: var(--color-sidebar-surface);'), true)
})

test('legacy dataset sidebar still keeps dataset naming helpers', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'), 'utf-8')

  assert.equal(source.includes('function datasetFriendlyName(tableName) {'), true)
  assert.equal(source.includes("/__\\d{6,}(?=__|$)/g"), true)
  assert.equal(source.includes(':title="ds.table_name"'), true)
})

test('chat keeps composer pinned as footer and improves assistant readability', () => {
  const leftPaneSource = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue'), 'utf-8')
  const chatHistorySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(leftPaneSource.includes('class="min-h-0 flex-1 flex flex-col p-3 sm:p-4 pb-0"'), true)
  assert.equal(leftPaneSource.includes(':style="leftPaneBodyStyle"'), false)
  assert.equal(chatHistorySource.includes('class="chat-markdown-content final-response-body max-w-none"'), true)
  assert.equal(chatHistorySource.includes('class="ephemeral-trace-list"'), true)
  assert.equal(chatHistorySource.includes('class="view-code-meta-badge"'), true)
})
