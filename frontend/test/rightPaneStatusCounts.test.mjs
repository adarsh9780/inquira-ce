import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace right pane supports one searchable result selector and lazy result renderers', () => {
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')
  const source = readFileSync(rightPanePath, 'utf-8')

  assert.equal(source.includes('HeaderDropdown'), true)
  assert.equal(source.includes('v-model="selectedResultId"'), true)
  assert.equal(source.includes(':searchable="resultOptions.length > 10"'), true)
  assert.equal(source.includes('defineAsyncComponent'), true)
  assert.equal(source.includes("defineAsyncComponent(() => import('../analysis/TableTab.vue'))"), true)
  assert.equal(source.includes("defineAsyncComponent(() => import('../analysis/FigureTab.vue'))"), true)
  assert.equal(source.includes("defineAsyncComponent(() => import('../analysis/OutputTab.vue'))"), true)
  assert.equal(source.includes("import TableTab from '../analysis/TableTab.vue'"), false)
  assert.equal(source.includes("import FigureTab from '../analysis/FigureTab.vue'"), false)
  assert.equal(source.includes('<SegmentedControl'), false)
  assert.equal(source.includes('dataPaneOptions'), false)
  assert.equal(source.includes('rounded-xl border p-1'), false)
  assert.equal(source.includes('buildUnifiedResultItems'), true)
  assert.equal(source.includes('appStore.dataframes'), true)
  assert.equal(source.includes('appStore.figures'), true)
  assert.equal(source.includes('appStore.scalars'), true)
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
  assert.equal(source.includes('subscribeWorkspaceArtifactUsage'), true)
})

test('figure renderer keeps contextual export actions while selection lives in Results', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('>Figure:</label>'), false)
  assert.equal(source.includes('id="figure-select"'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('Chart Ready'), false)
  assert.equal(source.includes('>Fullscreen<'), false)
  assert.equal(source.includes('>PNG<'), false)
  assert.equal(source.includes('>HTML<'), false)
  assert.equal(source.includes(":title=\"isDownloading ? 'Exporting chart' : 'Export chart'\""), true)
  assert.equal(source.includes("label: 'Delete chart'"), true)
  assert.equal(source.includes('PNG image (.png)'), true)
  assert.equal(source.includes('HTML file (.html)'), true)
  assert.equal(source.includes("import { persistExportFile } from '../../utils/exportFile'"), true)
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
