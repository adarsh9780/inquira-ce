import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('FigureTab uses active turn artifact catalog as canonical source and resolves selected chart by artifact id', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('const workspaceFigureArtifacts = ref([])'), true)
  assert.equal(source.includes('artifactApi.listTurn('), true)
  assert.equal(source.includes("'figure',"), true)
  assert.equal(source.includes('const liveFigureArtifacts = computed(() => {'), true)
  assert.equal(source.includes('return [...liveFigureArtifacts.value, ...persisted]'), true)
  assert.equal(source.includes('artifactStore.getSelectedFigureArtifact(workspaceStore.activeWorkspaceId)'), true)
  assert.equal(source.includes('artifactStore.setFigureCount(orderedFigures.value.length)'), true)
  assert.equal(source.includes('artifactApi.metadata('), true)
  assert.equal(source.includes('apiService.v1ListWorkspaceArtifacts('), false)
  assert.equal(source.includes('apiService.v1GetWorkspaceArtifactMetadata('), false)
  assert.equal(source.includes(':key="selectedArtifactId"'), true)
})

test('FigureTab keeps unavailable artifacts out of selectors and explains recovery in the empty state', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('<AppEmptyState'), true)
  assert.equal(source.includes("unavailableArtifactCount > 0 ? 'Saved charts unavailable'"), true)
  assert.equal(source.includes("artifactUnavailableDescription('chart', unavailableArtifactCount)"), true)
  assert.equal(source.includes('allPersistedFigureArtifacts.value.filter(isArtifactAvailable)'), true)
  assert.equal(source.includes('isArtifactPayloadMissingError(error)'), true)
  assert.equal(source.includes("v-else-if=\"artifactListError\""), false)
})
