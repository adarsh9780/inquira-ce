import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('native workspace data exposes local files and explicit Excel sheet selection', () => {
  const workspaceTab = read('src/components/modals/tabs/WorkspaceTab.vue')
  const settingsCoordinator = read('src/composables/useWorkspaceSettings.ts')
  assert.match(workspaceTab, /Data sources/)
  assert.match(workspaceTab, /Add data source/)
  assert.match(workspaceTab, /CSV/)
  assert.match(workspaceTab, /Parquet/)
  assert.match(workspaceTab, /Excel/)
  assert.match(workspaceTab, /Select sheets/)
  assert.match(workspaceTab, /source_object_id/)
  assert.match(workspaceTab, /formula_mode/)
  assert.match(workspaceTab, /connectionService/)
  assert.match(workspaceTab, /Managed Python/)
  assert.match(workspaceTab, /Company Python/)
  assert.match(workspaceTab, /Internal mirror/)
  assert.match(workspaceTab, /Package index/)
  assert.match(workspaceTab, /HTTP proxy/)
  assert.match(workspaceTab, /system certificates/i)
  assert.match(settingsCoordinator, /normalized === 'data' \? 'connections'/)
  assert.doesNotMatch(workspaceTab, /Upload a dataset/)
})

test('connection service uses the Wails bridge for every connection operation', () => {
  const service = read('src/services/connectionService.js')
  assert.match(service, /DiscoverLocalConnection/)
  assert.match(service, /CreateLocalConnection/)
  assert.match(service, /RefreshConnection/)
  assert.match(service, /DeleteConnection/)
  assert.match(service, /isNative/)
})

test('native file picker accepts modern Excel workbooks without claiming legacy xls support', () => {
  const app = read('../app.go')
  assert.match(app, /\*\.xlsx;\*\.XLSX/)
  assert.doesNotMatch(app, /\*\.xls;/)
})

test('native workspace exposes an analysis catalog built from connection snapshots', () => {
  const app = read('../app.go')
  const service = read('src/api/workspaces.ts')
  assert.match(app, /PrepareWorkspaceCatalog/)
  assert.doesNotMatch(service, /v1BootstrapWorkspaceRuntime/)
})
