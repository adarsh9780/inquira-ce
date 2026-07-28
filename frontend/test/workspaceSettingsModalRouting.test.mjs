import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const source = readFileSync(
  resolve(process.cwd(), 'src/components/modals/SettingsModal.vue'),
  'utf8',
)

test('workspace settings route is applied before workspace refresh completes', () => {
  const watcherStart = source.indexOf('() => props.modelValue')
  const routeInitialization = source.indexOf('initializePanelState(props.initialTab)', watcherStart)
  const workspaceRefresh = source.indexOf('await appStore.fetchWorkspaces()', watcherStart)

  assert.notEqual(watcherStart, -1)
  assert.notEqual(routeInitialization, -1)
  assert.notEqual(workspaceRefresh, -1)
  assert.equal(routeInitialization < workspaceRefresh, true)
})

test('workspace refresh failure does not reject the settings watcher', () => {
  assert.match(
    source,
    /try\s*\{\s*await appStore\.fetchWorkspaces\(\)\s*\}\s*catch \(error\) \{/,
  )
  assert.match(source, /Failed to refresh workspaces while opening settings:/)
})
