import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('native runtime setup supports company Python mirrors proxies and certificate bundles', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const service = read('src/services/runtimeProvisionService.js')
  const app = read('../app.go')

  assert.match(workspace, /Company Python/)
  assert.match(workspace, /Internal mirror/)
  assert.match(workspace, /Custom CA bundle/)
  assert.match(workspace, /choosePythonExecutable/)
  assert.match(workspace, /chooseCertificateBundle/)
  assert.match(workspace, /type="password"[^>]*v-model="runtimeConfig\.defaultIndex"/)
  assert.match(workspace, /type="password"[^>]*v-model="runtimeConfig\.httpProxy"/)
  assert.match(workspace, /type="password"[^>]*v-model="runtimeConfig\.httpsProxy"/)
  assert.match(workspace, /runtimeProvisionService\.plan/)
  assert.match(workspace, /Change runtime/)
  assert.match(workspace, /clearTransientRuntimeConfig/)
  assert.match(workspace, /runtimeProvisionError/)
  assert.match(service, /callWails\('RuntimePlan'/)
  assert.match(service, /callWails\('ChoosePythonExecutable'/)
  assert.match(service, /callWails\('ChooseCertificateBundle'/)
  assert.match(app, /func \(a \*App\) ChoosePythonExecutable/)
  assert.match(app, /func \(a \*App\) ChooseCertificateBundle/)
})

test('runtime setup keeps only safe successful configuration in status', () => {
  const provisioner = read('../internal/runtimeprovision/provisioner.go')
  const config = read('../internal/runtimeprovision/config.go')

  assert.match(config, /type SavedConfig struct/)
  assert.doesNotMatch(config, /type SavedConfig struct \{[^}]*HTTPProxy/s)
  assert.doesNotMatch(config, /type SavedConfig struct \{[^}]*DefaultIndex/s)
  assert.match(provisioner, /Configuration\s+\*SavedConfig/)
  assert.match(provisioner, /saveConfiguration/)
  assert.match(provisioner, /PlanPreview/)
  assert.match(provisioner, /redactProvisionError/)
})
