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
    'async function createWorkspace(name, schemaContext = \'\') {',
    'async function activateWorkspace(workspaceId) {',
  )

  assert.equal(createBlock.includes('const ws = await apiService.v1CreateWorkspace(name, schemaContext)'), true)
  assert.equal(createBlock.includes('await activateWorkspace(ws.id)'), true)
  assert.equal(createBlock.includes('await fetchWorkspaces()'), true)
})

test('workspace setup stepper captures shared context before dataset selection', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')
  const settingsPath = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(tabPath, 'utf-8')
  const settingsSource = readFileSync(settingsPath, 'utf-8')
  const storeSource = readFileSync(storePath, 'utf-8')
  const appSource = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('A workspace is meant for related datasets that share business meaning, terminology, and schema context.'), true)
  assert.equal(source.includes('{ id: 1, label: \'Workspace context\' }'), true)
  assert.equal(source.includes('{ id: 2, label: \'Select data\' }'), true)
  assert.equal(source.includes('{ id: 3, label: \'Generate schema\' }'), true)
  assert.equal(source.includes('await appStore.createWorkspace(name, context)'), true)
  assert.equal(source.includes('await appStore.renameWorkspace(workspaceId, name, context)'), true)
  assert.equal(source.includes('Creating workspace inside Settings...'), true)
  assert.equal(source.includes('Preparing workspace runtime inside Settings...'), true)
  assert.equal(source.includes('await appStore.ensureWorkspaceKernelConnected(workspaceId)'), true)
  assert.equal(source.includes('waitForCreateRuntimeToSettle'), false)
  assert.equal(source.includes("toast.success('Workspace ready', 'Workspace is ready for dataset selection.')"), true)
  assert.equal(source.includes('settingsWebSocket.subscribeComplete'), false)
  assert.equal(source.includes("const emit = defineEmits(['navigate', 'set-active-workspace', 'workspace-operation-change', 'workspace-created'])"), true)
  assert.equal(source.includes("emit('workspace-operation-change', {"), true)
  assert.equal(source.includes("emit('workspace-created', {"), true)
  assert.equal(source.includes("setWorkspaceOperation('create', 'Creating workspace and preparing its runtime.')"), true)
  assert.equal(source.includes("setWorkspaceOperation('ingest', 'Importing selected datasets into the workspace.')"), true)
  assert.equal(source.includes("setWorkspaceOperation('schema', 'Generating workspace schemas from the selected datasets.')"), true)
  assert.equal(settingsSource.includes("const activeWorkspaceOperation = ref('')"), true)
  assert.equal(settingsSource.includes('@workspace-operation-change="setActiveWorkspaceOperation"'), true)
  assert.equal(settingsSource.includes('notifyWorkspaceOperationBlocked()'), true)
  assert.equal(settingsSource.includes("if (activeSection.value === 'workspace')"), true)
  assert.equal(settingsSource.includes("toast.info(\n    'Workspace setup in progress'"), true)
  assert.equal(appSource.includes('data-testid="workspace-runtime-dialog"'), false)
  assert.equal(appSource.includes('const startupOverlayActive = computed(() => {'), true)
  assert.equal(appSource.includes('return Boolean(appBootstrap.active)'), true)
  assert.equal(storeSource.includes('suppressWorkspaceRuntimeOverlay'), false)
  assert.equal(appSource.includes('suppressWorkspaceRuntimeOverlay'), false)
})

test('workspace creation carries step one identity into dataset selection automatically', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')
  const settingsPath = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const source = readFileSync(tabPath, 'utf-8')
  const settingsSource = readFileSync(settingsPath, 'utf-8')
  const createBlock = extractBlock(
    source,
    'async function createWorkspace({ setupStep: targetSetupStep = 2 } = {}) {',
    'function schemaGenerationLabel(tableName) {',
  )

  assert.equal(source.includes('@click="continueFromWorkspaceIdentity()"'), true)
  assert.equal(source.includes('async function continueFromWorkspaceIdentity() {'), true)
  assert.equal(source.includes("await createWorkspace({ setupStep: normalized })"), true)
  assert.equal(source.includes("toast.info('Create workspace first'"), false)
  assert.equal(source.includes('requestedSetupStep'), true)
  assert.equal(source.includes('workspaceIdentityDraft'), true)
  assert.equal(source.includes('function resolveWorkspaceIdentityDraft() {'), true)
  assert.equal(createBlock.includes("emit('workspace-created', {"), true)
  assert.equal(createBlock.includes('setupWorkspaceName.value = \'\''), false)
  assert.equal(createBlock.includes('setupWorkspaceContext.value = \'\''), false)
  assert.equal(settingsSource.includes(':requested-setup-step="workspaceDetailSetupStep"'), true)
  assert.equal(settingsSource.includes(':workspace-identity-draft="workspaceIdentityDraft"'), true)
  assert.equal(settingsSource.includes('@workspace-created="handleWorkspaceCreated"'), true)
  assert.equal(settingsSource.includes('function handleWorkspaceCreated(payload) {'), true)
  assert.equal(settingsSource.includes("navigateTo('ws-detail', 'forward')"), true)
})

test('workspace flow routes through settings panels and workspace list/detail/create modes', () => {
  const settingsPath = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')

  const settingsSource = readFileSync(settingsPath, 'utf-8')
  const tabSource = readFileSync(tabPath, 'utf-8')

  assert.equal(settingsSource.includes('openWorkspaceSection'), true)
  assert.equal(settingsSource.includes("panelClass('ws-list')"), true)
  assert.equal(settingsSource.includes("panelClass('ws-detail')"), true)
  assert.equal(settingsSource.includes("panelClass('ws-create')"), true)
  assert.equal(tabSource.includes("panelMode === 'ws-list'"), true)
  assert.equal(tabSource.includes("panelMode === 'ws-detail'"), true)
  assert.equal(tabSource.includes("@click=\"emit('navigate', 'ws-create', 'forward')\""), true)
  assert.equal(tabSource.includes("@click=\"emit('navigate', 'ws-list', 'backward')\""), true)
  assert.equal(tabSource.includes('title="Refresh dataset"'), true)
  assert.equal(tabSource.includes('title="Remove dataset"'), true)
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
