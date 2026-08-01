import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('native workspace data exposes supported files and explicit multi-object selection', () => {
  const workspaceTab = read('src/components/modals/tabs/WorkspaceTab.vue')
  const workspaceDataSources = read('src/components/schema/WorkspaceDataSources.vue')
  const settingsCoordinator = read('src/composables/useWorkspaceSettings.ts')
  assert.match(workspaceDataSources, /Data sources/)
  assert.match(workspaceDataSources, /Add data/)
  assert.match(workspaceDataSources, /CSV/)
  assert.match(workspaceDataSources, /Parquet/)
  assert.match(workspaceDataSources, /Excel/)
  assert.match(workspaceDataSources, /JSON/)
  assert.match(workspaceDataSources, /SQLite/)
  assert.match(workspaceDataSources, /Sheets/)
  assert.match(workspaceDataSources, /Tables and views/)
  assert.match(workspaceDataSources, /previewObject/)
  assert.match(workspaceDataSources, /HeaderDropdown/)
  assert.doesNotMatch(workspaceDataSources, /<select/)
  assert.match(workspaceTab, /formula_mode/)
  assert.match(workspaceTab, /connectionService/)
  assert.match(workspaceTab, /Managed Python/)
  assert.match(workspaceTab, /Company Python/)
  assert.match(workspaceTab, /Internal mirror/)
  assert.match(workspaceTab, /Package index/)
  assert.match(workspaceTab, /HTTP proxy/)
  assert.match(workspaceTab, /system certificates/i)
  assert.match(settingsCoordinator, /\['data', 'connections'\]\.includes\(normalized\) \? 'runtime'/)
  assert.doesNotMatch(workspaceTab, /Upload a dataset/)
})

test('connection service uses the Wails bridge for every connection operation', () => {
  const service = read('src/services/connectionService.ts')
  assert.match(service, /DiscoverLocalConnection/)
  assert.match(service, /CreateLocalConnection/)
  assert.match(service, /RefreshConnection/)
  assert.match(service, /DeleteConnection/)
  assert.match(service, /isNative/)
})

test('native file picker accepts the supported data-source matrix without claiming legacy xls support', () => {
  const app = read('../app.go')
  assert.match(app, /\*\.xlsx;\*\.XLSX/)
  assert.match(app, /\*\.json;\*\.JSON/)
  assert.match(app, /\*\.sqlite;\*\.SQLITE/)
  assert.doesNotMatch(app, /\*\.xls;/)
})

test('native workspace exposes an analysis catalog built from connection snapshots', () => {
  const app = read('../app.go')
  const service = read('src/api/workspaces.ts')
  assert.match(app, /PrepareWorkspaceCatalog/)
  assert.doesNotMatch(service, /v1BootstrapWorkspaceRuntime/)
})
