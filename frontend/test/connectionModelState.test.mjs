import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf-8')

test('frontend data context comes only from workspace summaries and the column catalog', () => {
  const store = read('src/stores/appStore.js')
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const contextBar = read('src/components/layout/WorkspaceContextBar.vue')
  const chatInput = read('src/components/chat/ChatInput.vue')
  const codeTab = read('src/components/analysis/CodeTab.vue')
  const commandRegistry = read('src/services/commandRegistry.js')

  for (const source of [store, setup, contextBar, chatInput, codeTab, commandRegistry]) {
    assert.doesNotMatch(source, /\bdataFilePath\b/)
    assert.doesNotMatch(source, /\bingestedTableName\b/)
    assert.doesNotMatch(source, /\bingestedColumns\b/)
    assert.doesNotMatch(source, /\bhasDataFile\b/)
  }

  assert.match(setup, /activeWorkspaceSummary\?\.table_count/)
  assert.match(contextBar, /activeWorkspaceSummary\?\.table_count/)
  assert.match(chatInput, /activeWorkspaceSummary\?\.table_names/)
  assert.match(chatInput, /appStore\.columnCatalog/)
  assert.match(codeTab, /activeWorkspaceSummary\?\.table_names/)
  assert.match(codeTab, /appStore\.columnCatalog/)
  assert.match(commandRegistry, /activeWorkspaceSummary\?\.table_names/)
})

test('obsolete workspace-path helpers and bridge are removed', () => {
  const apiService = read('src/api/native.ts')
  const app = read('../app.go')

  assert.doesNotMatch(apiService, /\bgetSettings\s*\(/)
  assert.doesNotMatch(apiService, /\bgetDatabasePaths\s*\(/)
  assert.doesNotMatch(apiService, /\bv1GetWorkspacePaths\s*\(/)
  assert.doesNotMatch(apiService, /requireWailsMethod\('GetWorkspacePaths'\)/)
  assert.doesNotMatch(app, /type WorkspacePaths struct/)
  assert.doesNotMatch(app, /func \(a \*App\) GetWorkspacePaths/)
})
