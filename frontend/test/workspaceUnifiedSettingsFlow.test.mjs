import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace settings uses one summary and editor surface', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const template = workspace.slice(0, workspace.indexOf('<script setup>'))

  assert.equal(settings.includes('Active Details'), false)
  assert.equal(settings.includes("panelClass('workspace')"), true)
  assert.equal(settings.includes("panelClass('ws-list')"), false)
  assert.equal(settings.includes("panelClass('ws-detail')"), false)
  assert.equal(settings.includes("panelClass('ws-create')"), false)
  assert.equal(workspace.includes("const workspaceSurface = ref('summary')"), true)
  assert.equal(workspace.includes("workspaceSurface === 'summary'"), true)
  assert.equal(workspace.includes('Selected Workspace Summary'), true)
  assert.equal(template.includes('workspace-stepper'), false)
  assert.equal(template.includes('System Pipeline Graph'), false)
  assert.equal(template.includes('Workspace runtime'), false)
})

test('new workspace is created from an autofocus inline row and opens the combined editor', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspace.includes('ref="newWorkspaceInputRef"'), true)
  assert.equal(workspace.includes('@keydown.enter.prevent="createWorkspace"'), true)
  assert.equal(workspace.includes('async function beginInlineCreate()'), true)
  assert.equal(workspace.includes('newWorkspaceInputRef.value?.focus?.()'), true)
  assert.equal(workspace.includes("editorOpenedAfterCreate.value = true"), true)
  assert.equal(workspace.includes("workspaceSurface.value = 'editor'"), true)
  assert.equal(workspace.includes('← Back to workspace summary'), true)
  assert.equal(workspace.includes("editorOpenedAfterCreate ? 'Set up' : 'Edit'"), true)
  assert.equal(workspace.includes('Quick create + Enter'), false)
})

test('combined editor saves context explicitly and accepts desktop file drops', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspace.includes('Save context'), true)
  assert.equal(workspace.includes('@click="saveWorkspaceContext"'), true)
  assert.equal(workspace.includes('async function saveWorkspaceContext()'), true)
  assert.equal(workspace.includes('@drop.prevent="handleDatasetDrop"'), true)
  assert.equal(workspace.includes("new Set(['.csv', '.tsv', '.parquet', '.json', '.xlsx', '.xls'])"), true)
  assert.equal(workspace.includes('await startBatchDatasetIngestion(droppedPaths)'), true)
  assert.equal(workspace.includes("filters: [{ name: 'Data files', extensions: ['csv', 'parquet', 'xlsx', 'xls', 'json', 'tsv'] }]"), true)
})

test('selected summary exposes activate edit and rename actions', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspace.includes('@click="selectWorkspaceSummary(workspace.id)"'), true)
  assert.equal(workspace.includes('@click="activateSelectedWorkspace"'), true)
  assert.equal(workspace.includes('@click="openWorkspaceEditor"'), true)
  assert.equal(workspace.includes('@click="startRename"'), true)
})

test('selected summary keeps actions separate from metrics and uses one create entry point', () => {
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const template = workspace.slice(0, workspace.indexOf('<script setup>'))

  assert.equal(template.includes('<span>New workspace</span>'), false)
  assert.equal(template.includes('class="grid grid-cols-2 gap-x-6 gap-y-3"'), true)
  assert.equal(template.includes('class="grid min-w-0 flex-1 grid-cols-3 gap-3"'), false)
  assert.equal(template.match(/@click="beginInlineCreate"/g)?.length, 2)
})

test('workspace editor clearly separates selection, saved context, and file import actions', () => {
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
  assert.equal(template.includes('data-testid="workspace-import-datasets-dropzone"'), true)
  assert.equal(template.includes(':disabled="isDatasetIngesting || isDeletingDataset || requiresWorkspaceActivation"'), true)
  assert.equal(template.includes('data-testid="workspace-import-datasets-header"'), false)
  assert.equal(template.includes('data-testid="workspace-import-datasets-empty"'), false)
  assert.equal(template.match(/CSV, TSV, Parquet, JSON, XLSX, and XLS/g)?.length, 1)
})
