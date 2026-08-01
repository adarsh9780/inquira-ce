import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('workspace settings separate General, Runtime, and AI without duplicating data-source management', () => {
  const workspace = [
    read('src/components/modals/tabs/WorkspaceTab.vue'),
    read('src/composables/useWorkspaceSettings.ts'),
  ].join('\n')

  assert.match(workspace, /aria-label="Workspace settings sections"/)
  assert.match(workspace, /role="tablist"/)
  assert.match(workspace, /\{ id: 'general', label: 'General' \}/)
  assert.match(workspace, /\{ id: 'runtime', label: 'Runtime' \}/)
  assert.match(workspace, /\{ id: 'ai', label: 'AI' \}/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'general'"/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'runtime'"/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'ai'"/)
  assert.match(workspace, /props\.initialSection/)
  assert.match(workspace, /moveWorkspaceSection\(-1, \$event\)/)
  assert.match(workspace, /moveWorkspaceSection\(1, \$event\)/)
})

test('data entry points route to Workspace Data while AI opens scoped settings', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const store = read('src/stores/uiStore.ts')
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const composer = read('src/components/chat/ChatInput.vue')

  assert.match(settings, /:initial-section="workspaceInitialSection"/)
  assert.match(store, /settingsInitialTab\.value = 'workspace-ai'/)
  assert.match(store, /function requestConnectionFlow\(\)[\s\S]*activeTab\.value = 'schema-editor'/)
  assert.match(store, /function requestConnectionFlow\(\)[\s\S]*isSettingsOpen\.value = false/)
  assert.match(setup, /openDataConnectionFlow\(\)/)
  assert.match(setup, /openSettings\('workspace-ai'\)/)
  assert.doesNotMatch(composer, /<ModelSelector/)
})

test('runtime status stays visible while workspace actions contain current controls', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.match(workspace, /\{\{ runtimeStatusLabel \}\}/)
  assert.match(workspace, /aria-label="Workspace actions"/)
  assert.match(workspace, />Rename workspace</)
  assert.match(workspace, />Delete workspace</)
  assert.doesNotMatch(workspace, />Retry runtime</)
  assert.doesNotMatch(workspace, />Reset runtime</)
})
