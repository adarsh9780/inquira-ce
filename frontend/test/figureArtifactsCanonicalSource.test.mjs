import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('FigureTab uses active turn artifact catalog as canonical source and resolves selected chart by artifact id', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('const workspaceFigureArtifacts = ref([])'), true)
  assert.equal(source.includes('artifactApi.listTurn('), true)
  assert.equal(source.includes("'figure',"), true)
  assert.equal(source.includes('const liveFigureArtifacts = computed(() => {'), true)
  assert.equal(source.includes('return [...liveFigureArtifacts.value, ...persisted]'), true)
  assert.equal(source.includes('appStore.getSelectedFigureArtifact(appStore.activeWorkspaceId)'), true)
  assert.equal(source.includes('appStore.setFigureCount(orderedFigures.value.length)'), true)
  assert.equal(source.includes('artifactApi.metadata('), true)
  assert.equal(source.includes('apiService.v1ListWorkspaceArtifacts('), false)
  assert.equal(source.includes('apiService.v1GetWorkspaceArtifactMetadata('), false)
  assert.equal(source.includes(':key="selectedArtifactId"'), true)
})

test('FigureTab renders artifact load errors inside the centered empty state instead of the toolbar', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('<AppEmptyState'), true)
  assert.equal(source.includes(":title=\"artifactListError ? 'Charts unavailable' : 'No saved charts'\""), true)
  assert.equal(source.includes(":description=\"artifactListError || 'Ask AI for a chart, or promote one from Runs.'\""), true)
  assert.equal(source.includes("v-else-if=\"artifactListError\""), false)
})
