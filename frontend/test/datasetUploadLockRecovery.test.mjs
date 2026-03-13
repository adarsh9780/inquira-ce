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

test('dataset upload retries once after resetting the kernel on workspace lock conflicts', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')
  const uploadBlock = extractBlock(
    source,
    'async uploadDataPath(filePath) {',
    'let columns = []',
  )

  assert.equal(uploadBlock.includes('const isWorkspaceLockConflict ='), true)
  assert.equal(uploadBlock.includes("normalizedDetail.includes('workspace database is currently locked')"), true)
  assert.equal(uploadBlock.includes('await this.v1ResetWorkspaceKernel(workspaceId)'), true)
  assert.equal(uploadBlock.includes('await appStore.ensureWorkspaceKernelConnected(workspaceId)'), true)
  assert.equal(
    uploadBlock.includes('ds = await this.v1AddDataset(workspaceId, filePath)'),
    true,
  )
})
