import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('layout defines elevated light surfaces for sidebar and active workspace panes', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(styleSource.includes('--color-shell-backdrop: #F3F4F6;'), true)
  assert.equal(styleSource.includes('--color-sidebar-surface: #F7F7F8;'), true)
  assert.equal(styleSource.includes('--color-workspace-surface: #FFFFFF;'), true)

  assert.equal(appSource.includes('class="flex-1 flex overflow-hidden app-shell-frame relative"'), true)
  assert.equal(appSource.includes('class="h-full shrink-0 app-nav-pane"'), true)
  assert.equal(appSource.includes('class="flex-1 flex flex-col overflow-hidden app-workspace-pane"'), true)
  assert.equal(appSource.includes('.app-nav-pane {'), true)
  assert.equal(appSource.includes('.app-workspace-pane {'), true)

  assert.equal(sidebarSource.includes('background-color: var(--color-sidebar-surface);'), true)
})

test('sidebar datasets use friendly labels while preserving full identifiers', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('function datasetFriendlyName(tableName) {'), true)
  assert.equal(source.includes('/__\\d{6,}(?=__|$)/g'), true)
  assert.equal(source.includes('{{ datasetFriendlyName(ds.table_name) }}'), true)
  assert.equal(source.includes(':title="ds.table_name"'), true)
  assert.equal(source.includes('function datasetSourceCaption(filePath) {'), true)
})

test('chat flow anchors composer for short histories and improves assistant readability', () => {
  const leftPaneSource = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue'), 'utf-8')
  const chatHistorySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(leftPaneSource.includes('const shouldAnchorComposerToHistory = computed(() => {'), true)
  assert.equal(leftPaneSource.includes("return { flex: '0 0 auto' }"), true)
  assert.equal(leftPaneSource.includes(':style="leftPaneBodyStyle"'), true)

  assert.equal(chatHistorySource.includes('class="chat-markdown-content final-response-body max-w-none"'), true)
  assert.equal(chatHistorySource.includes(':deep(.chat-markdown-content) {\n  font-size: 15px;\n  line-height: 1.6;'), true)
  assert.equal(chatHistorySource.includes(':deep(.final-response-body) {\n  font-size: 16px;\n  line-height: 1.6;'), true)
  assert.equal(chatHistorySource.includes('CodeBracketIcon'), true)
  assert.equal(chatHistorySource.includes('View Code'), true)
})

test('table styling increases density and adds row/column tracking cues', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/TableTab.vue'), 'utf-8')

  assert.equal(source.includes('--ag-row-height: 30px;'), true)
  assert.equal(source.includes('--ag-cell-horizontal-padding: 8px;'), true)
  assert.equal(source.includes('--ag-even-row-background-color: #FAFAFA;'), true)
  assert.equal(source.includes('--ag-header-background-color: #F4F4F5;'), true)
  assert.equal(source.includes('.ag-theme-quartz .ag-cell,'), true)
  assert.equal(source.includes('.ag-theme-quartz .ag-header-cell {'), true)
  assert.equal(source.includes('title="Search rows"'), true)
  assert.equal(source.includes('title="Search rows in current table"'), true)
})
