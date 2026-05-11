import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('active turn payload syncs the editor code and keys pane state by active turn', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('setPythonFileContent(activeTurnCode.value)'), true)
  assert.equal(source.includes("return `${workspaceKey}::${turnKey || 'workspace'}::${artifactKey}`"), true)
  assert.equal(source.includes("return `${workspaceKey}::${turnKey || 'workspace'}`"), true)
})

test('TableTab scopes persisted artifacts to selected turn ids while still allowing live artifacts', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/TableTab.vue'), 'utf-8')

  assert.equal(source.includes('const activeTurnArtifactIds = computed(() => {'), true)
  assert.equal(source.includes('const livePersistedArtifactIds = computed(() => {'), true)
  assert.equal(source.includes('const scopedPersistedArtifacts = computed(() => {'), true)
  assert.equal(source.includes('...activeTurnArtifactIds.value,'), true)
  assert.equal(source.includes('...livePersistedArtifactIds.value,'), true)
  assert.equal(source.includes('const persistedArtifacts = scopedPersistedArtifacts.value.map((artifact) => ({'), true)
})

test('FigureTab scopes persisted artifacts to selected turn ids while still allowing live artifacts', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'), 'utf-8')

  assert.equal(source.includes('const activeTurnFigureArtifactIds = computed(() => {'), true)
  assert.equal(source.includes('const livePersistedFigureIds = computed(() => {'), true)
  assert.equal(source.includes('const scopedWorkspaceFigureArtifacts = computed(() => {'), true)
  assert.equal(source.includes('...activeTurnFigureArtifactIds.value,'), true)
  assert.equal(source.includes('...livePersistedFigureIds.value,'), true)
  assert.equal(source.includes("const persisted = scopedWorkspaceFigureArtifacts.value.map((fig) => ({ ...fig, source: 'artifact' }))"), true)
})
