import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('app store maintains active turn state through relation and workspace-tree loaders', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = [
    '../src/stores/appStore.js',
    '../src/stores/conversationStore.ts',
    '../src/stores/artifactStore.ts',
  ].map((path) => readFileSync(resolve(testDir, path), 'utf-8')).join('\n')

  assert.equal(source.includes('turnViewEnabled'), false)
  assert.equal(source.includes('const activeTurnId = ref(\'\')'), true)
  assert.match(source, /const activeTurn = ref[^(]*\(null\)/)
  assert.equal(source.includes('const activeTurnCode = ref(\'\')'), true)
  assert.equal(source.includes('activeTurnArtifacts'), false)
  assert.match(source, /const activeTurnRelations = ref[^(]*\(null\)/)
  assert.equal(source.includes('activeTurnTree'), false)
  assert.equal(source.includes('const activeTurnArtifactRefreshKey = ref(0)'), true)
  assert.match(source, /const workspaceTurnTree = ref[^(]*\(null\)/)
  assert.equal(source.includes('const finalTurnId = ref(\'\')'), true)
  assert.equal(source.includes('function setActiveTurnId(turnId) {'), true)
  assert.equal(source.includes('activeTurnId.value = String(turnId || \'\').trim()'), true)
  assert.equal(source.includes('function hydrateArtifactsFromToolEvents(toolEvents)'), true)
  assert.equal(source.includes('hydrateArtifactsFromToolEvents(payload?.current?.tool_events)'), true)
  assert.equal(source.includes('activeTurnArtifactRefreshKey.value += 1'), true)
  assert.equal(source.includes("data: Array.isArray(artifact?.preview_rows) ? artifact.preview_rows : []"), true)
  assert.equal(source.includes('const figure = normalizePlotlyFigure(artifact?.payload?.figure ?? artifact?.payload)'), true)
  assert.equal(source.includes('async function loadActiveTurnRelations('), true)
  assert.equal(source.includes('loadActiveTurnTree'), false)
  assert.equal(source.includes('async function loadWorkspaceTurnTree('), true)
  assert.equal(source.includes('const preferredTurnId = String(activeTurnId.value || \'\').trim()'), true)
  assert.equal(source.includes('async function fetchConversationTurns({ preferLatest = false } = {})'), true)
  assert.equal(source.includes('const targetTurnId = preferLatest ? newestTurnId : (preferredTurnId || newestTurnId)'), true)
  assert.equal(source.includes('async function loadFinalTurn('), true)
  assert.equal(source.includes('function setLastMessageTurnId(turnId, messageId = null, options = {})'), true)
  assert.equal(source.includes('loadActiveTurnRelations,'), true)
  assert.equal(source.includes('loadWorkspaceTurnTree,'), true)
})
