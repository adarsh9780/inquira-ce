import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8')

test('slash commands execute through the native Go bridge', () => {
  const api = read('src/api/execution.ts')
  const goApp = read('../app.go')

  assert.match(api, /invokeNative\('ExecuteWorkspaceCommand'/)
  assert.match(goApp, /func \(a \*App\) ExecuteWorkspaceCommand/)
})

test('Terms are bundled and loaded through the native Go bridge', () => {
  const api = read('src/api/preferences.ts')
  const goApp = read('../app.go')

  assert.match(api, /invokeNative\('GetTermsAndConditions'/)
  assert.match(goApp, /func \(a \*App\) GetTermsAndConditions/)
})

test('desktop identity and window constraints match release 0.5.35', () => {
  const config = JSON.parse(read('../wails.json'))
  const main = read('../main.go')

  assert.equal(config.info.productVersion, '0.5.35')
  assert.equal(config.info.productName, 'Inquira')
  assert.equal(config.info.companyName, 'Inquira')
  assert.match(main, /Width:\s+1400/)
  assert.match(main, /MinWidth:\s+768/)
  assert.match(main, /MinHeight:\s+600/)
})
