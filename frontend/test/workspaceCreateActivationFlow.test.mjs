import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace creation activates the new workspace centrally in the store', () => {
  const source = read('src/stores/appStore.js')
  const start = source.indexOf("async function createWorkspace(name, schemaContext = '') {")
  const end = source.indexOf('async function activateWorkspace(workspaceId) {', start)
  const block = source.slice(start, end)

  assert.equal(block.includes('const ws = await apiService.v1CreateWorkspace(name, schemaContext)'), true)
  assert.equal(block.includes('await activateWorkspace(ws.id)'), true)
  assert.equal(block.includes('await fetchWorkspaces()'), true)
})

test('workspace creation opens inline context editing on the active workspace summary while warming runtime', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const settings = read('src/components/modals/SettingsModal.vue')

  assert.equal(workspace.includes('async function createWorkspace()'), true)
  assert.equal(workspace.includes('await appStore.createWorkspace(name, context)'), true)
  assert.equal(workspace.includes('isEditingContext.value = true'), true)
  assert.equal(workspace.includes('workspaceSurface'), false)
  assert.equal(workspace.includes('async function warmWorkspaceRuntimeInBackground(workspaceId)'), true)
  assert.equal(workspace.includes('void warmWorkspaceRuntimeInBackground(workspaceId)'), true)
  assert.equal(settings.includes('@workspace-created="handleWorkspaceCreated"'), true)
  assert.equal(settings.includes("currentPanel.value = 'ws-detail'"), false)
})

test('existing workspace summary supports inspect-first activation and active-only editing', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const settings = read('src/components/modals/SettingsModal.vue')

  assert.equal(workspace.includes('const requiresWorkspaceActivation = computed(() => !isWorkspaceActive.value)'), true)
  assert.equal(workspace.includes("emit('select-workspace', id)"), true)
  assert.equal(workspace.includes("emit('activate-workspace', id)"), true)
  assert.equal(workspace.includes('v-if="isWorkspaceActive && !isEditingContext"'), true)
  assert.equal(workspace.includes('v-if="isWorkspaceActive" type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="startRename"'), true)
  assert.equal(workspace.includes('function startContextEdit()'), true)
  assert.equal(settings.includes('@select-workspace="selectWorkspace"'), true)
  assert.equal(settings.includes('@activate-workspace="activateWorkspace"'), true)
})

test('workspace activation updates active state immediately without waiting for a list refresh', () => {
  const store = read('src/stores/appStore.js')
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const start = store.indexOf('async function activateWorkspace(workspaceId) {')
  const end = store.indexOf('async function renameWorkspace(', start)
  const activationBlock = store.slice(start, end)

  assert.equal(activationBlock.includes('activeWorkspaceId.value = workspaceId'), true)
  assert.equal(activationBlock.includes('workspaces.value = workspaces.value.map((workspace) => ({'), true)
  assert.equal(activationBlock.includes('is_active: workspace.id === workspaceId'), true)
  assert.equal(workspace.includes('workspace.id === appStore.activeWorkspaceId'), true)
  assert.equal(workspace.includes("activeWorkspace.value.id === String(appStore.activeWorkspaceId || '').trim()"), true)
})

test('workspace launchers open the unified workspace settings surface without step routing', () => {
  const paths = [
    'src/components/WorkspaceSwitcher.vue',
    'src/components/layout/UnifiedSidebar.vue',
    'src/components/layout/sidebar/SidebarWorkspaces.vue',
  ]

  for (const path of paths) {
    const source = read(path)
    assert.equal(source.includes("openSettings('workspace')"), true)
    assert.equal(source.includes("openSettings('workspace', 1)"), false)
  }
  assert.equal(read('src/App.vue').includes('initial-step'), false)
  assert.equal(read('src/stores/appStore.js').includes('settingsInitialStep'), false)
})
