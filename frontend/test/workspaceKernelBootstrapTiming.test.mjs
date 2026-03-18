import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `Missing marker: ${startMarker}`)
  assert.notEqual(end, -1, `Missing marker: ${endMarker}`)
  return source.slice(start, end)
}

test('workspace list flow bootstraps kernel only for single-workspace sessions', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(appStorePath, 'utf-8')

  const fetchBlock = extractBlock(
    source,
    'async function fetchWorkspaces() {',
    'async function createWorkspace(name) {',
  )
  const createBlock = extractBlock(
    source,
    'async function createWorkspace(name) {',
    'async function activateWorkspace(workspaceId) {',
  )
  const activateBlock = extractBlock(
    source,
    'async function activateWorkspace(workspaceId) {',
    'async function fetchConversations() {',
  )

  assert.equal(
    fetchBlock.includes('if (items.length === 1 && activeWorkspaceId.value === items[0]?.id) {'),
    true,
  )
  assert.equal(fetchBlock.includes('await ensureWorkspaceKernelConnected(activeWorkspaceId.value)'), true)
  assert.equal(createBlock.includes('ensureWorkspaceKernelConnected('), false)
  assert.equal(activateBlock.includes('ensureWorkspaceKernelConnected('), false)
})

test('dataset upload path is the runtime bootstrap trigger', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')
  const uploadBlock = extractBlock(
    source,
    'async uploadDataPath(filePath) {',
    'return {',
  )
  assert.equal(
    uploadBlock.includes('await appStore.ensureWorkspaceKernelConnected(workspaceId)'),
    true,
  )
})
