import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('layout defines elevated light surfaces for sidebar and active workspace panes', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(styleSource.includes('--color-shell-backdrop: #F5F4EF;'), true)
  assert.equal(styleSource.includes('--color-sidebar-surface: #EFEDE8;'), true)
  assert.equal(styleSource.includes('--color-workspace-surface: #FAF9F6;'), true)

  assert.equal(appSource.includes('class="flex-1 flex overflow-hidden app-shell-frame relative"'), true)
  assert.equal(appSource.includes('class="app-sidebar-rail"'), false)
  assert.equal(appSource.includes('@mouseenter="expandSidebarFromRail()"'), false)
  assert.equal(appSource.includes('class="h-full shrink-0 app-nav-pane"'), true)
  assert.equal(appSource.includes(":class=\"{ 'app-nav-pane-collapsed': appStore.isSidebarCollapsed }\""), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
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
  assert.equal(source.includes('return parts[parts.length - 1] || normalized'), true)
})

test('chat keeps composer pinned as footer and improves assistant readability', () => {
  const leftPaneSource = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue'), 'utf-8')
  const chatHistorySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(leftPaneSource.includes("class=\"min-h-0 flex-1 flex flex-col p-3 sm:p-4 pb-0\""), true)
  assert.equal(leftPaneSource.includes(':style="leftPaneBodyStyle"'), false)

  assert.equal(chatHistorySource.includes('class="chat-markdown-content final-response-body max-w-none"'), true)
  assert.equal(chatHistorySource.includes(':deep(.chat-markdown-content) {\n  font-size: 14px;\n  line-height: 1.7;'), true)
  assert.equal(chatHistorySource.includes(':deep(.final-response-body) {\n  font-size: 14px;\n  line-height: 1.7;'), true)
  assert.equal(chatHistorySource.includes('style="color: var(--color-accent);"'), true)
  assert.equal(chatHistorySource.includes('const SHOW_EPHEMERAL_TRACE = true'), true)
  assert.equal(chatHistorySource.includes('class="thinking-block"'), true)
  assert.equal(chatHistorySource.includes('&lt;/&gt; View code'), true)
  assert.equal(chatHistorySource.includes('class="view-code-meta-badge"'), true)
  assert.equal(chatHistorySource.includes('CodeBracketIcon'), true)
  assert.equal(chatHistorySource.includes('Generated code details'), false)
})

test('table styling increases density and adds row/column tracking cues', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/TableTab.vue'), 'utf-8')

  assert.equal(source.includes('--ag-row-height: 30px;'), true)
  assert.equal(source.includes('--ag-cell-horizontal-padding: 8px;'), true)
  assert.equal(source.includes('--ag-even-row-background-color: #F5F3EE;'), true)
  assert.equal(source.includes('--ag-row-hover-color: #EDE9E3;'), true)
  assert.equal(source.includes('--ag-header-background-color: #EFEDE8;'), true)
  assert.equal(source.includes('--ag-active-color: #C96A2E;'), true)
  assert.equal(source.includes('.ag-theme-quartz .ag-cell,'), true)
  assert.equal(source.includes('.ag-theme-quartz .ag-header-cell {'), true)
  assert.equal(source.includes('.ag-theme-quartz .ag-paging-panel {'), true)
  assert.equal(source.includes('title="Search rows"'), true)
  assert.equal(source.includes('title="Search rows in current table"'), true)
})

test('status bar uses neutral metadata badges instead of accent pills for row-count viewport info', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes("const artifactCountClass = computed(() => {"), true)
  assert.equal(source.includes("return 'bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)]'"), true)
  assert.equal(source.includes("class=\"flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium\" :class=\"artifactCountClass\""), true)
  assert.equal(source.includes("bg-[var(--color-accent)]/10 text-[var(--color-accent)]"), false)
})
