import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('state ownership is split across six typed domain stores', () => {
  const storeNames = [
    'workspaceStore.ts',
    'conversationStore.ts',
    'executionStore.ts',
    'artifactStore.ts',
    'preferencesStore.ts',
    'uiStore.ts',
  ]

  for (const storeName of storeNames) {
    const path = `src/stores/${storeName}`
    assert.equal(existsSync(resolve(process.cwd(), path)), true, path)
    assert.match(read(path), /defineStore\(/, path)
  }

  assert.equal(existsSync(resolve(process.cwd(), 'src/stores/appStore.js')), false)
  const coordinator = read('src/stores/appCoordinatorStore.js')
  for (const storeName of storeNames) {
    assert.match(coordinator, new RegExp(`from './${storeName.replace(/\.ts$/, '')}'`))
  }
})

test('ordinary API calls use the generated domain adapter and legacy API files are removed', () => {
  assert.equal(existsSync(resolve(process.cwd(), 'src/services/apiService.js')), false)
  assert.equal(existsSync(resolve(process.cwd(), 'src/services/contracts/v1Api.js')), false)

  const adapter = read('src/services/apiClient.ts')
  const runtime = read('src/services/apiRuntime.js')
  assert.match(adapter, /from '.\/generatedApi'/)
  assert.match(runtime, /domainApi as v1Api/)
  assert.match(runtime, /parseSseBuffer/)
  assert.match(runtime, /@tauri-apps\/api\/core/)
})
