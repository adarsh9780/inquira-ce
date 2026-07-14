import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('workspace AI API keeps defaults overrides effective values and readiness separate', () => {
  const contract = read('src/services/contracts/v1Api.js')
  const store = read('src/stores/appStore.js')

  assert.match(contract, /workspaces\/\$\{workspaceId\}\/ai-config/)
  assert.match(contract, /ai-config\/overrides/)
  assert.match(store, /workspaceAIConfig/)
  assert.match(store, /fetchWorkspaceAIConfig/)
  assert.match(store, /saveWorkspaceAIConfig/)
  assert.match(store, /resetWorkspaceAIConfig/)
})

test('workspace AI editor inherits application defaults and keeps privacy workspace scoped', () => {
  const source = read('src/components/modals/tabs/WorkspaceAIConfigSection.vue')

  assert.match(source, /Use application defaults/)
  assert.match(source, /Application credential/)
  assert.match(source, /Main model/)
  assert.match(source, /Lite model/)
  assert.match(source, /This permission applies only to this workspace/)
  assert.match(source, /Advanced generation controls/)
  assert.doesNotMatch(source, /api_key/)
})

test('first-run surfaces follow workspace data connection configuration readiness order', () => {
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const chat = read('src/components/chat/ChatTab.vue')
  const store = read('src/stores/appStore.js')

  assert.match(setup, /Workspace/)
  assert.match(setup, /Model connection/)
  assert.match(setup, /Workspace AI/)
  assert.match(chat, /Create your first workspace/)
  assert.match(chat, /Add data to begin/)
  assert.match(chat, /Connect a model/)
  assert.match(chat, /Review workspace AI/)
  assert.match(chat, /Summarize this dataset/)
  assert.match(store, /state: 'no_workspace'/)
  assert.match(store, /state: 'no_data'/)
  assert.match(store, /state: 'model_connection_required'/)
  assert.match(store, /state: 'workspace_configuration_required'/)
  assert.match(store, /state: 'ready'/)
})
