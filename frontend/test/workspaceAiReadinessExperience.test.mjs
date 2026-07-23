import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('native workspace AI keeps defaults overrides and effective values separate', () => {
  const store = read('src/stores/appStore.js')
  const service = read('src/services/apiService.js')

  assert.match(store, /workspaceAIConfig/)
  assert.match(store, /fetchWorkspaceAIConfig/)
  assert.match(store, /saveWorkspaceAIConfig/)
  assert.doesNotMatch(store, /if \(workspaceService\.isNative\(\)\) \{\s*workspaceAIConfig\.value = null/)
  assert.match(service, /requireWailsMethod\('GetWorkspaceAIConfig'\)/)
  assert.match(service, /requireWailsMethod\('UpdateWorkspaceAIConfig'\)/)
  assert.match(read('../app.go'), /func \(a \*App\) GetWorkspaceAIConfig/)
  assert.match(read('../app.go'), /func \(a \*App\) UpdateWorkspaceAIConfig/)
})

test('workspace AI editor inherits application defaults and keeps privacy workspace scoped', () => {
  const source = read('src/components/modals/tabs/WorkspaceAIConfigSection.vue')

  assert.match(source, /Use application defaults/)
  assert.match(source, /Models &amp; privacy/)
  assert.match(source, /Manage connection/)
  assert.match(source, /Application credential/)
  assert.match(source, /Main model/)
  assert.match(source, /Lite model/)
  assert.match(source, /Coding model/)
  assert.match(source, /This permission applies only to this workspace/)
  assert.match(source, /Advanced generation controls/)
  assert.doesNotMatch(source, /api_key/)
})

test('native workspace settings expose the AI section selected by readiness actions', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const settings = read('src/components/modals/SettingsModal.vue')
  const store = read('src/stores/appStore.js')

  assert.match(workspace, /const workspaceSections = \[[\s\S]*?\{ id: 'general', label: 'General' \}[\s\S]*?\{ id: 'connections', label: 'Data sources' \}[\s\S]*?\{ id: 'ai', label: 'AI' \}/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'ai'"/)
  assert.doesNotMatch(workspace, /!isNativeWorkspaceMetadata && activeWorkspaceSection === 'ai'/)
  assert.match(settings, /candidate === 'models' \|\| candidate === 'workspace-ai'/)
  assert.match(store, /n === 'models' \|\| n === 'workspace-ai'/)
})

test('settings puts workspace models with workspace data and isolates credentials', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const connections = read('src/components/modals/tabs/LLMSettingsTab.vue')
  const chatInput = read('src/components/chat/ChatInput.vue')

  assert.match(settings, /<span>Workspaces<\/span>/)
  assert.match(settings, /<span>AI providers<\/span>/)
  assert.doesNotMatch(settings, /<span>Models<\/span>/)
  assert.ok(settings.indexOf('<span>Workspaces</span>') < settings.indexOf('<span>AI providers</span>'))
  assert.match(workspace, /<WorkspaceAIConfigSection/)
  assert.match(workspace, /activeWorkspaceSection === 'connections'/)
  assert.match(workspace, /activeWorkspaceSection === 'ai'/)
  assert.ok(workspace.indexOf("activeWorkspaceSection === 'connections'") < workspace.indexOf("activeWorkspaceSection === 'ai'"))
  assert.match(connections, /API Credentials/)
  assert.match(connections, /:aria-expanded="applicationDefaultsOpen"/)
  assert.match(connections, /motion-disclosure-open/)
  assert.doesNotMatch(chatInput, /<ModelSelector/)
  assert.match(chatInput, /effectiveWorkspaceModel/)
})

test('first-run surfaces connect a model before workspace and data setup', () => {
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const chat = read('src/components/chat/ChatTab.vue')
  const readiness = read('src/components/chat/WorkspaceReadinessJourney.vue')
  const store = read('src/stores/appStore.js')

  assert.match(setup, /Workspace/)
  assert.match(setup, /AI provider/)
  assert.match(setup, /Data sources/)
  assert.match(setup, /Workspace AI/)
  assert.ok(setup.indexOf("key: 'connection'") < setup.indexOf("key: 'workspace'"))
  assert.ok(setup.indexOf("key: 'workspace'") < setup.indexOf("key: 'configuration'"))
  assert.ok(setup.indexOf("key: 'configuration'") < setup.indexOf("key: 'data'"))
  assert.match(chat, /<WorkspaceReadinessJourney/)
  assert.match(readiness, /Create a workspace/)
  assert.match(readiness, /Connect your data/)
  assert.match(readiness, /Connect an AI provider/)
  assert.match(readiness, /Review workspace AI/)
  assert.match(chat, /Summarize this dataset/)
  assert.match(store, /state: 'no_workspace'/)
  assert.match(store, /state: 'no_data'/)
  assert.match(store, /state: 'model_connection_required'/)
  assert.match(store, /state: 'workspace_configuration_required'/)
  assert.match(store, /state: 'ready'/)
  assert.ok(store.indexOf('!aiReadiness.credential_ready') < store.indexOf('const tableCount = Number(activeWorkspaceSummary'))
  assert.ok(store.indexOf('!aiReadiness.model_ready') < store.indexOf('const tableCount = Number(activeWorkspaceSummary'))
})
