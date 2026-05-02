import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('app store exposes active turn state and loaders', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('const turnViewEnabled = ref(true)'), true)
  assert.equal(source.includes('const activeTurnId = ref(\'\')'), true)
  assert.equal(source.includes('const activeTurn = ref(null)'), true)
  assert.equal(source.includes('const activeTurnCode = ref(\'\')'), true)
  assert.equal(source.includes('const activeTurnArtifacts = ref([])'), true)
  assert.equal(source.includes('const activeTurnRelations = ref(null)'), true)
  assert.equal(source.includes('const finalTurnId = ref(\'\')'), true)
  assert.equal(source.includes('function hydrateArtifactsFromToolEvents(toolEvents)'), true)
  assert.equal(source.includes('hydrateArtifactsFromToolEvents(payload?.current?.tool_events)'), true)
  assert.equal(source.includes("data: Array.isArray(artifact?.preview_rows) ? artifact.preview_rows : []"), true)
  assert.equal(source.includes('const figure = normalizePlotlyFigure(artifact?.payload?.figure ?? artifact?.payload)'), true)
  assert.equal(source.includes('async function loadActiveTurn('), true)
  assert.equal(source.includes('async function loadActiveTurnRelations('), true)
  assert.equal(source.includes('async function loadFinalTurn('), true)
  assert.equal(source.includes('function setLastMessageTurnId(turnId)'), true)
})
