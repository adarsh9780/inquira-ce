import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('workspace settings separate General, Data, and AI without losing workspace context', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.match(workspace, /aria-label="Workspace settings sections"/)
  assert.match(workspace, /role="tablist"/)
  assert.match(workspace, /\{ id: 'general', label: 'General' \}/)
  assert.match(workspace, /\{ id: 'data', label: 'Data' \}/)
  assert.match(workspace, /\{ id: 'ai', label: 'AI' \}/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'general'"/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'data'"/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'ai'"/)
  assert.match(workspace, /props\.initialSection/)
  assert.match(workspace, /moveWorkspaceSection\(-1, \$event\)/)
  assert.match(workspace, /moveWorkspaceSection\(1, \$event\)/)
})

test('workspace entry points deep-link to the relevant scoped tab', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const store = read('src/stores/appStore.js')
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const composer = read('src/components/chat/ChatInput.vue')

  assert.match(settings, /:initial-section="workspaceInitialSection"/)
  assert.match(store, /settingsInitialTab\.value = 'workspace-ai'/)
  assert.match(store, /settingsInitialTab\.value = 'workspace-data'/)
  assert.match(setup, /openSettings\('workspace-data'\)/)
  assert.match(setup, /openSettings\('workspace-ai'\)/)
  assert.match(composer, /@manage-models="appStore\.openSettings\('workspace-ai'\)"/)
})

test('runtime status stays visible while maintenance actions remain secondary', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.match(workspace, /\{\{ runtimeStatusLabel \}\}/)
  assert.match(workspace, /aria-label="Workspace actions"/)
  assert.match(workspace, />Retry runtime</)
  assert.match(workspace, />Reset runtime</)
  assert.match(workspace, />Delete workspace</)
})
