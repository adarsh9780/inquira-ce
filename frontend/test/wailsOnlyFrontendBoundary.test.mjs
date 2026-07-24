import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const frontendRoot = resolve(process.cwd())
const sourceRoot = resolve(frontendRoot, 'src')

test('frontend package keeps one direct Wails bridge architecture', () => {
  const packageJson = JSON.parse(readFileSync(resolve(frontendRoot, 'package.json'), 'utf8'))
  const apiService = readFileSync(resolve(sourceRoot, 'api/native.ts'), 'utf8')
  assert.equal(packageJson.scripts.build, 'vite build')
  assert.match(apiService, /window\.go\?\.main\?\.App/)
  assert.match(apiService, /requireNativeMethod/)
})

test('frontend omits retired workflow wrappers while retaining catalog preparation', () => {
  const apiService = readFileSync(resolve(sourceRoot, 'api/native.ts'), 'utf8')
  const app = readFileSync(resolve(frontendRoot, '..', 'app.go'), 'utf8')
  const retiredWrappers = [
    'v1ResetWorkspaceAIConfig',
    'v1RerunFinalTurn',
    'v1BootstrapWorkspaceRuntime',
  ]

  for (const wrapper of retiredWrappers) {
    assert.equal(apiService.includes(wrapper), false)
  }
  assert.match(app, /func \(a \*App\) PrepareWorkspaceCatalog\(/)
})

test('interactive terminal keeps its Wails implementation under runtime-neutral names', () => {
  const terminalTab = readFileSync(
    resolve(sourceRoot, 'components/analysis/TerminalTab.vue'),
    'utf8',
  )
  const terminalService = readFileSync(
    resolve(sourceRoot, 'services/nativeTerminalService.ts'),
    'utf8',
  )

  assert.match(terminalTab, /<NativeTerminalPane\b[\s\S]*?\/>/)
  assert.match(terminalService, /StartTerminalSession/)
  assert.match(terminalService, /WriteTerminalSession/)
  assert.match(terminalService, /ResizeTerminalSession/)
  assert.match(terminalService, /StopTerminalSession/)
})

test('data import and export use the connection model and native-neutral filters', () => {
  const app = readFileSync(resolve(sourceRoot, 'App.vue'), 'utf8')
  const workspace = readFileSync(
    resolve(sourceRoot, 'components/modals/tabs/WorkspaceTab.vue'),
    'utf8',
  )
  const exportFile = readFileSync(resolve(sourceRoot, 'utils/exportFile.ts'), 'utf8')

  assert.equal(app.includes('startGlobalDatasetImport'), false)
  assert.match(workspace, /connectionService\.chooseFile\(\)/)
  assert.match(exportFile, /nativeFilters/)
  assert.match(app, /openDataConnectionFlow/)
})
