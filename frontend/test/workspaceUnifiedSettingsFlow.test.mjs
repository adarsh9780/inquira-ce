import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace settings uses one active-workspace management surface', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const template = workspace.slice(0, workspace.indexOf('<script setup>'))

  assert.equal(settings.includes('Active Details'), false)
  assert.equal(settings.includes("panelClass('workspace')"), true)
  assert.equal(settings.includes("panelClass('ws-list')"), false)
  assert.equal(settings.includes("panelClass('ws-detail')"), false)
  assert.equal(settings.includes("panelClass('ws-create')"), false)
  assert.equal(workspace.includes('workspaceSurface'), false)
  assert.equal(workspace.includes('Workspace settings'), true)
  assert.equal(workspace.includes('Selected Workspace Summary'), false)
  assert.equal(template.includes('workspace-stepper'), false)
  assert.equal(template.includes('System Pipeline Graph'), false)
  assert.equal(template.includes('Workspace runtime'), false)
})

test('new workspace is created from an autofocus inline row and opens inline context editing', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspace.includes('ref="newWorkspaceInputRef"'), true)
  assert.equal(workspace.includes('@keydown.enter.prevent="createWorkspace"'), true)
  assert.equal(workspace.includes('async function beginInlineCreate()'), true)
  assert.equal(workspace.includes('newWorkspaceInputRef.value?.focus?.()'), true)
  assert.equal(workspace.includes('isEditingContext.value = true'), true)
  assert.equal(workspace.includes('← Back to workspace summary'), false)
  assert.equal(workspace.includes('Quick create + Enter'), false)
})

test('active workspace summary saves context and opens the native connection flow', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspace.includes('@click="saveWorkspaceContext"'), true)
  assert.equal(workspace.includes('async function saveWorkspaceContext()'), true)
  assert.equal(workspace.includes('@click="chooseConnectionFile"'), true)
  assert.equal(workspace.includes('connectionService.discover('), true)
  assert.equal(workspace.includes('connectionService.create('), true)
  assert.equal(workspace.includes('@drop.prevent="handleDatasetDrop"'), false)
  assert.equal(workspace.includes('startBatchDatasetIngestion'), false)
})

test('selected summary exposes only activation until the workspace is active', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspace.includes('@click="selectWorkspaceSummary(workspace.id)"'), true)
  assert.equal(workspace.includes('@click="activateSelectedWorkspace"'), true)
  assert.equal(workspace.includes('@click="startContextEdit"'), true)
  assert.equal(workspace.includes('v-if="isWorkspaceActive && !isEditingContext"'), true)
  assert.equal(workspace.includes('@click="runWorkspaceAction(startRename)"'), true)
  assert.equal(workspace.includes('v-if="isWorkspaceActive" type="button" class="nav-tab w-full text-left" @click="runWorkspaceAction(startRename)"'), true)
  assert.equal(workspace.includes('@click="openWorkspaceEditor"'), false)
})

test('selected summary puts actions in the header and uses context instead of duplicate metrics', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const template = workspace.slice(0, workspace.indexOf('<script setup>'))

  assert.equal(template.includes('<span>New workspace</span>'), false)
  assert.equal(template.includes('Workspace Context'), true)
  assert.equal(template.includes('No workspace context added yet.'), true)
  assert.equal(workspace.includes('const selectedWorkspaceContext = computed('), true)
  assert.equal(workspace.includes('workspaceDetail.value = null'), true)
  assert.equal(template.includes('<span class="section-label mb-1 block">Conversations</span>'), false)
  assert.equal(template.includes('<span class="section-label mb-1 block">Last Active</span>'), false)
  assert.equal(template.includes('flex min-w-0 items-center justify-between gap-3 border-b'), true)
  assert.equal(template.includes('Add data source'), true)
  assert.equal(template.includes('@click="chooseConnectionFile"'), true)
  assert.equal(template.match(/@click="beginInlineCreate"/g)?.length, 2)
})

test('settings sidebar keeps workspace ownership ahead of shared connections', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const template = settings.slice(0, settings.indexOf('<script setup>'))

  assert.equal(template.includes('Workspace Setup'), false)
  assert.equal(template.includes('App Config'), false)
  assert.equal(template.includes('User &amp; System'), false)
  assert.equal(template.includes('Switch &amp; Create'), false)
  assert.equal(template.includes('<span>Models</span>'), false)
  assert.equal(template.indexOf('<span>Workspaces</span>') < template.indexOf('<span>AI providers</span>'), true)
  assert.equal(template.indexOf('<span>AI providers</span>') < template.indexOf('<span>Appearance</span>'), true)
  assert.equal(template.indexOf('<span>Appearance</span>') < template.indexOf('<span>Account</span>'), true)
})

test('active workspace summary separates selection, saved context, and connection actions', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const template = workspace.slice(0, workspace.indexOf('<script setup>'))

  assert.equal(template.includes('workspace.id === activeWorkspaceId'), true)
  assert.equal(template.includes('>Selected</span>'), true)
  assert.equal(template.includes('opacity-40 transition-all'), true)
  assert.equal(template.includes('focus-visible:opacity-100 group-hover:opacity-100'), true)
  assert.equal(workspace.includes("const savedWorkspaceContext = ref('')"), true)
  assert.equal(workspace.includes('const isWorkspaceContextDirty = computed('), true)
  assert.equal(template.includes(':disabled="isSavingWorkspaceIdentity || !isWorkspaceContextDirty"'), true)
  assert.equal(template.includes("isWorkspaceContextDirty ? 'Unsaved changes' : 'Saved'"), true)
  assert.equal(template.includes('data-testid="workspace-import-datasets-dropzone"'), false)
  assert.equal(template.includes('v-if="isWorkspaceActive"'), true)
  assert.equal(template.includes('Add data source'), true)
  assert.equal(template.includes('No data sources yet'), true)
  assert.equal(template.includes('CSV, Parquet, or Excel'), true)
  assert.equal(workspace.includes('pendingConnection'), true)
  assert.equal(workspace.includes('nativeConnections'), true)
  assert.equal(workspace.includes('isDatasetIngesting'), false)
})
