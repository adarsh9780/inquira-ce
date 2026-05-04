import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace API contract and store expose rename and clear database actions', () => {
  const contractPath = resolve(process.cwd(), 'src/services/contracts/v1Api.js')
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')

  const contract = readFileSync(contractPath, 'utf-8')
  const service = readFileSync(servicePath, 'utf-8')
  const store = readFileSync(storePath, 'utf-8')

  assert.equal(contract.includes('rename: (workspaceId, name, schemaContext = undefined)'), true)
  assert.equal(contract.includes('clearDatabase: (workspaceId)'), true)
  assert.equal(service.includes('async v1RenameWorkspace(workspaceId, name, schemaContext = undefined)'), true)
  assert.equal(service.includes('async v1ClearWorkspaceDatabase(workspaceId)'), true)
  assert.equal(store.includes('async function renameWorkspace(workspaceId, name, schemaContext = undefined)'), true)
  assert.equal(store.includes('async function clearWorkspaceDatabase(workspaceId)'), true)
})

test('dataset API contract exposes async batch ingestion and polling', () => {
  const contractPath = resolve(process.cwd(), 'src/services/contracts/v1Api.js')
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')

  const contract = readFileSync(contractPath, 'utf-8')
  const service = readFileSync(servicePath, 'utf-8')
  const tab = readFileSync(tabPath, 'utf-8')

  assert.equal(contract.includes('addBatch: (workspaceId, sourcePaths)'), true)
  assert.equal(contract.includes('ingestionById: (workspaceId, jobId)'), true)
  assert.equal(service.includes('async v1AddDatasetsBatch(workspaceId, sourcePaths)'), true)
  assert.equal(service.includes('async v1GetDatasetIngestionJob(workspaceId, jobId)'), true)
  assert.equal(tab.includes('multiple: true'), true)
  assert.equal(tab.includes('await appStore.ensureWorkspaceKernelConnected(workspaceId)'), true)
  assert.equal(tab.includes('await apiService.v1AddDatasetsBatch(workspaceId, sourcePaths)'), true)
})
