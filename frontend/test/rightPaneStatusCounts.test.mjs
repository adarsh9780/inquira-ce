import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace right pane supports icon tabs and compact dropdown switcher without inline count badges', () => {
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')
  const source = readFileSync(rightPanePath, 'utf-8')

  assert.equal(source.includes('v-if="useCompactPaneSwitcher"'), true)
  assert.equal(source.includes('HeaderDropdown'), true)
  assert.equal(source.includes('COMPACT_SWITCHER_THRESHOLD_PX'), true)
  assert.equal(source.includes('ResizeObserver'), true)
  assert.equal(source.includes('title="Table"'), true)
  assert.equal(source.includes('title="Chart"'), true)
  assert.equal(source.includes('title="Output"'), true)
  assert.equal(source.includes('<span class="sr-only">Table</span>'), true)
  assert.equal(source.includes('<span class="sr-only">Chart</span>'), true)
  assert.equal(source.includes('<span class="sr-only">Output</span>'), true)
  assert.equal(source.includes('appStore.dataframes.length'), false)
  assert.equal(source.includes('appStore.figures.length'), false)
  assert.equal(source.includes('appStore.scalars.length'), false)
})

test('status bar renders pane count from canonical table/chart counts and keeps table viewport label in parallel', () => {
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(statusBarPath, 'utf-8')

  assert.equal(source.includes('const paneArtifactCountLabel = computed(() => {'), true)
  assert.equal(source.includes('Math.max('), true)
  assert.equal(source.includes('Number(appStore.dataframeCount || 0)'), true)
  assert.equal(source.includes('Number(appStore.figureCount || 0)'), true)
  assert.equal(source.includes('v-if="appStore.activeWorkspaceId && paneArtifactCountLabel"'), true)
  assert.equal(source.includes('v-if="appStore.activeWorkspaceId && tableViewportLabel"'), true)
  assert.equal(source.includes('showArtifactUsageWarning'), true)
  assert.equal(source.includes('artifactUsageWarningTitle'), true)
  assert.equal(source.includes('ExclamationTriangleIcon'), true)
  assert.equal(source.includes('apiService.v1GetWorkspaceArtifactUsage'), true)
})

test('figure tab header removes explicit Figure label next to dropdown', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('>Figure:</label>'), false)
  assert.equal(source.includes('id="figure-select"'), true)
  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('Chart Ready'), false)
  assert.equal(source.includes('>Fullscreen<'), false)
  assert.equal(source.includes('>PNG<'), false)
  assert.equal(source.includes('>HTML<'), false)
  assert.equal(source.includes("isDownloading ? 'Exporting...' : 'Export'"), true)
  assert.equal(source.includes('PNG image (.png)'), true)
  assert.equal(source.includes('HTML file (.html)'), true)
  assert.equal(source.includes('showSaveFilePicker'), true)
  assert.equal(source.includes('@tauri-apps/plugin-dialog'), true)
  assert.equal(source.includes('@tauri-apps/plugin-fs'), true)
})

test('app store keeps figureCount synchronized with setFigures output', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('figureCount.value = 0'), true)
  assert.equal(source.includes('figureCount.value = figures.value.length'), true)
})

test('api service exposes artifact usage summary endpoint helper', () => {
  const apiPath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiPath, 'utf-8')

  assert.equal(source.includes('async v1GetWorkspaceArtifactUsage(workspaceId, options = {})'), true)
  assert.equal(source.includes('/api/v1/workspaces/${workspaceId}/artifacts/usage'), true)
  assert.equal(source.includes('Artifact usage fetch failed'), true)
})
