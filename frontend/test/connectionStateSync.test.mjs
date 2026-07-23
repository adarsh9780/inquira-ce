import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `Missing marker: ${startMarker}`)
  assert.notEqual(end, -1, `Missing marker: ${endMarker}`)
  return source.slice(start, end)
}

test('connection mutations refresh active workspace readiness and column metadata', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'),
    'utf-8',
  )
  const refreshBlock = extractBlock(
    source,
    'async function refreshNativeConnectionState(workspaceId) {',
    'async function handlePendingConnectionFlowRequest() {',
  )
  const createBlock = extractBlock(
    source,
    'async function createPendingConnection() {',
    'async function refreshNativeConnection(connectionId) {',
  )
  const updateBlock = extractBlock(
    source,
    'async function refreshNativeConnection(connectionId) {',
    'async function deleteNativeConnection(connectionId) {',
  )
  const deleteBlock = extractBlock(
    source,
    'async function deleteNativeConnection(connectionId) {',
    'function connectionOutputSummary(connection) {',
  )

  assert.match(refreshBlock, /loadNativeConnections\(\)/)
  assert.match(refreshBlock, /appStore\.fetchActiveWorkspaceSummary\(normalizedWorkspaceId\)/)
  assert.match(refreshBlock, /appStore\.fetchColumnCatalog\(\{ force: true \}\)/)
  assert.match(createBlock, /await refreshNativeConnectionState\(workspaceId\)/)
  assert.match(updateBlock, /await refreshNativeConnectionState\(workspaceId\)/)
  assert.match(deleteBlock, /await refreshNativeConnectionState\(workspaceId\)/)
})
