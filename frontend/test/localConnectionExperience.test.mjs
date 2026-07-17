import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('native workspace data uses connection language and exposes CSV and Parquet first', () => {
  const workspaceTab = read('src/components/modals/tabs/WorkspaceTab.vue')
  assert.match(workspaceTab, /Connections/)
  assert.match(workspaceTab, /Add connection/)
  assert.match(workspaceTab, /CSV/)
  assert.match(workspaceTab, /Parquet/)
  assert.match(workspaceTab, /connectionService/)
  assert.doesNotMatch(workspaceTab, /Upload a dataset/)
})

test('connection service keeps Wails and legacy HTTP boundaries explicit', () => {
  const service = read('src/services/connectionService.js')
  assert.match(service, /DiscoverLocalConnection/)
  assert.match(service, /CreateLocalConnection/)
  assert.match(service, /RefreshConnection/)
  assert.match(service, /DeleteConnection/)
  assert.match(service, /isNative/)
})
