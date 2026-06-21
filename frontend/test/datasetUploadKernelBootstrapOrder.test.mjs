import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset upload boots the workspace runtime before calling the dataset import endpoint', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  const uploadStart = source.indexOf('async uploadDataPath(filePath) {')
  const runtimeConnect = source.indexOf('await appStore.ensureWorkspaceRuntimeReady(workspaceId)', uploadStart)
  const addDataset = source.indexOf('ds = await this.v1AddDataset(workspaceId, filePath)', uploadStart)

  assert.notEqual(uploadStart, -1)
  assert.notEqual(runtimeConnect, -1)
  assert.notEqual(addDataset, -1)
  assert.equal(runtimeConnect < addDataset, true)
})
