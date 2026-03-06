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

  assert.equal(contract.includes('rename: (workspaceId, name)'), true)
  assert.equal(contract.includes('clearDatabase: (workspaceId)'), true)
  assert.equal(service.includes('async v1RenameWorkspace(workspaceId, name)'), true)
  assert.equal(service.includes('async v1ClearWorkspaceDatabase(workspaceId)'), true)
  assert.equal(store.includes('async function renameWorkspace(workspaceId, name)'), true)
  assert.equal(store.includes('async function clearWorkspaceDatabase(workspaceId)'), true)
})
