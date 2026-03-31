import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `Missing marker: ${startMarker}`)
  assert.notEqual(end, -1, `Missing marker: ${endMarker}`)
  return source.slice(start, end)
}

test('workspace creation activates the new workspace centrally in the store', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')
  const createBlock = extractBlock(
    source,
    'async function createWorkspace(name) {',
    'async function activateWorkspace(workspaceId) {',
  )

  assert.equal(createBlock.includes('const ws = await apiService.v1CreateWorkspace(name)'), true)
  assert.equal(createBlock.includes('await activateWorkspace(ws.id)'), true)
  assert.equal(createBlock.includes('await fetchWorkspaces()'), true)
})

test('workspace create modal warns that creating a workspace switches active context', () => {
  const modalPath = resolve(process.cwd(), 'src/components/modals/WorkspaceCreateModal.vue')
  const source = readFileSync(modalPath, 'utf-8')

  assert.equal(
    source.includes('Your new workspace will become the active workspace right away.'),
    true,
  )
  assert.equal(
    source.includes('we will clean up its running resources first.'),
    true,
  )
  assert.equal(
    source.includes('You can switch back later from the workspace picker.'),
    true,
  )
  assert.equal(source.includes('Open Existing Workspace'), true)
  assert.equal(source.includes('Workspace names must be unique.'), true)
  assert.equal(source.includes('emit(\'open-workspace\''), true)
  assert.equal(source.includes('const duplicateWorkspace = computed(() => {'), true)
  assert.equal(source.includes('View details'), true)
  assert.equal(source.includes('const workspaceSummaryVisible = ref(false)'), true)
  assert.equal(source.includes('await apiService.v1GetWorkspaceSummary(workspaceId)'), true)
})

test('workspace launchers pass existing workspaces into the create modal', () => {
  const launcherPaths = [
    resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue'),
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue'),
  ]

  for (const filePath of launcherPaths) {
    const source = readFileSync(filePath, 'utf-8')
    assert.equal(source.includes(':workspaces="appStore.workspaces"'), true)
    assert.equal(source.includes(':active-workspace-id="appStore.activeWorkspaceId"'), true)
    assert.equal(source.includes('@open-workspace="openWorkspaceFromDialog"'), true)
  }
})

test('apiService exposes workspace summary route for lazy workspace detail loading', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/services/apiService.js'), 'utf-8')

  assert.equal(source.includes('async v1GetWorkspaceSummary(workspaceId) {'), true)
  assert.equal(source.includes('return v1Api.workspaces.summary(workspaceId)'), true)
})
