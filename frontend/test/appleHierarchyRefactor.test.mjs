import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('workspace panes share one restrained toolbar and segmented control system', () => {
  const left = read('src/components/layout/WorkspaceLeftPane.vue')
  const right = read('src/components/layout/WorkspaceRightPane.vue')
  const styles = read('src/style.css')

  assert.match(left, /<AppToolbar/)
  assert.match(right, /<AppToolbar/)
  assert.match(left, /<SegmentedControl/)
  assert.match(right, /<SegmentedControl/)
  assert.match(styles, /\.app-toolbar/)
  assert.match(styles, /\.segmented-control-item-active/)
})

test('sidebar progressively discloses workspace tools while preserving collapsed access', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.match(source, /<DisclosureSection[^>]+label="Workspace tools"/)
  assert.match(source, /v-else class="space-y-0\.5"/)
  assert.match(source, /title="Schema editor"/)
  assert.match(source, /title="Conversation tree"/)
})

test('composer uses inline setup guidance and progressive model management', () => {
  const composer = read('src/components/chat/ChatInput.vue')
  const selector = read('src/components/ui/ModelSelector.vue')

  assert.match(composer, /<InlineNotice/)
  assert.match(composer, /hasTurnNavigation/)
  assert.match(composer, /@manage-models="appStore\.openSettings\('workspace'\)"/)
  assert.match(selector, /Workspace model settings…/)
})

test('rare destructive result actions live in overflow menus', () => {
  const table = read('src/components/analysis/TableTab.vue')
  const figure = read('src/components/analysis/FigureTab.vue')

  assert.match(table, /title="Table actions"/)
  assert.match(table, /<FloatingActionMenu/)
  assert.match(table, /label: 'Delete table', destructive: true/)
  assert.match(figure, /label: 'Delete chart'.*destructive: true/)
  assert.match(figure, /:height="136"/)
})

test('empty states and token summary use the shared quiet hierarchy', () => {
  const chat = read('src/components/chat/ChatTab.vue')
  const output = read('src/components/analysis/OutputTab.vue')
  const figure = read('src/components/analysis/FigureTab.vue')
  const usage = read('src/utils/usageFormat.js')

  assert.match(chat, /<AppEmptyState/)
  assert.match(output, /<AppEmptyState/)
  assert.match(figure, /<AppEmptyState/)
  assert.match(usage, /in · .*out ·/)
})

test('flat model settings sections do not regain card borders on hover', () => {
  const styles = read('src/style.css')
  const hoverRule = styles.match(/\.llm-settings-container \.settings-card:hover \{([^}]+)\}/)?.[1] || ''

  assert.match(hoverRule, /border-color: transparent;/)
  assert.match(hoverRule, /border-top-color: var\(--color-border\);/)
})

test('result panes announce and mark new contextual output without moving focus', () => {
  const source = read('src/components/layout/WorkspaceRightPane.vue')

  assert.match(source, /aria-live="polite"/)
  assert.match(source, /newResultPanes/)
  assert.match(source, /markResultAvailable/)
  assert.doesNotMatch(source, /\.focus\(/)
})
