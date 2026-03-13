import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset upload boots the workspace kernel before calling the dataset import endpoint', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  const uploadStart = source.indexOf('async uploadDataPath(filePath) {')
  const kernelConnect = source.indexOf('await appStore.ensureWorkspaceKernelConnected(workspaceId)', uploadStart)
  const addDataset = source.indexOf('ds = await this.v1AddDataset(workspaceId, filePath)', uploadStart)

  assert.notEqual(uploadStart, -1)
  assert.notEqual(kernelConnect, -1)
  assert.notEqual(addDataset, -1)
  assert.equal(kernelConnect < addDataset, true)
})
