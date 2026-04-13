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

test('workspace flow supports settings-driven initial step handoff and dataset-management mode', () => {
  const settingsPath = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')
  const stepperPath = resolve(process.cwd(), 'src/components/modals/WorkspaceStepper.vue')

  const settingsSource = readFileSync(settingsPath, 'utf-8')
  const tabSource = readFileSync(tabPath, 'utf-8')
  const stepperSource = readFileSync(stepperPath, 'utf-8')

  assert.equal(settingsSource.includes('initialStep: {'), true)
  assert.equal(settingsSource.includes(':initial-step="initialStep"'), true)
  assert.equal(tabSource.includes('const normalizedInitialStep = computed(() => {'), true)
  assert.equal(tabSource.includes('const isDatasetManagementMode = computed(() => normalizedInitialStep.value === 2)'), true)
  assert.equal(stepperSource.includes('title="Refresh from source file"'), true)
  assert.equal(stepperSource.includes('title="Remove dataset from workspace"'), true)
  assert.equal(stepperSource.includes('Add another dataset'), true)
  assert.equal(stepperSource.includes('Done'), true)
})

test('workspace launchers open settings modal at workspace step 1 instead of old create modal', () => {
  const launcherPaths = [
    resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue'),
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue'),
  ]

  for (const filePath of launcherPaths) {
    const source = readFileSync(filePath, 'utf-8')
    assert.equal(source.includes('WorkspaceCreateModal'), false)
    assert.equal(source.includes('SettingsModal'), true)
    assert.equal(source.includes('initial-step'), true)
  }
})

test('apiService exposes workspace summary route for lazy workspace detail loading', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/services/apiService.js'), 'utf-8')

  assert.equal(source.includes('async v1GetWorkspaceSummary(workspaceId) {'), true)
  assert.equal(source.includes('return v1Api.workspaces.summary(workspaceId)'), true)
})
