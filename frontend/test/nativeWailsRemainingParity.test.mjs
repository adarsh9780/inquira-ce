import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8')

test('slash commands execute through the native Go bridge', () => {
  const api = read('src/services/apiService.js')
  const goApp = read('../app.go')

  assert.match(api, /app\?\.ExecuteWorkspaceCommand/)
  assert.match(api, /app\?\.ListWorkspaceCommands/)
  assert.match(goApp, /func \(a \*App\) ExecuteWorkspaceCommand/)
  assert.match(goApp, /func \(a \*App\) ListWorkspaceCommands/)
})

test('Terms are bundled and loaded without FastAPI in Wails', () => {
  const api = read('src/services/apiService.js')
  const goApp = read('../app.go')

  assert.match(api, /app\?\.GetTermsAndConditions/)
  assert.match(goApp, /func \(a \*App\) GetTermsAndConditions/)
})

test('native artifact usage updates do not open an HTTP SSE stream', () => {
  const api = read('src/services/apiService.js')
  const method = api.slice(
    api.indexOf('async subscribeWorkspaceArtifactUsage'),
    api.indexOf('async v1Logout'),
  )

  assert.match(method, /v1GetWorkspaceArtifactUsage/)
  assert.match(method, /nativeWailsApp/)
  assert.doesNotMatch(method, /text\/event-stream[\s\S]*nativeWailsApp/)
})

test('desktop identity and window constraints match Rust version 0.5.35', () => {
  const config = JSON.parse(read('../wails.json'))
  const main = read('../main.go')

  assert.equal(config.info.productVersion, '0.5.35')
  assert.equal(config.info.productName, 'Inquira')
  assert.equal(config.info.companyName, 'Inquira')
  assert.match(main, /Width:\s+1400/)
  assert.match(main, /MinWidth:\s+800/)
  assert.match(main, /MinHeight:\s+600/)
})
