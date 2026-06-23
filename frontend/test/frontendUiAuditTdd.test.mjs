import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

function walkVueFiles(dir) {
  const files = []
  for (const entry of readdirSync(dir)) {
    const fullPath = resolve(dir, entry)
    const stats = statSync(fullPath)
    if (stats.isDirectory()) {
      files.push(...walkVueFiles(fullPath))
    } else if (fullPath.endsWith('.vue')) {
      files.push(fullPath)
    }
  }
  return files
}

test('floating action menus use the shared primitive across audited surfaces', () => {
  const primitive = read('src/components/ui/FloatingActionMenu.vue')
  const sidebarMenu = read('src/components/layout/sidebar/SidebarConversationActionsMenu.vue')
  const workspaceSwitcher = read('src/components/WorkspaceSwitcher.vue')
  const turnTreeActions = read('src/components/chat/TurnTreeNodeActions.vue')
  const figureTab = read('src/components/analysis/FigureTab.vue')

  assert.equal(primitive.includes('data-floating-action-menu'), true)
  assert.equal(primitive.includes('data-floating-action-menu-divider'), true)
  assert.equal(primitive.includes("emit('select'"), true)
  assert.equal(primitive.includes("emit('close'"), true)
  assert.equal(primitive.includes('clampedPosition'), true)

  for (const source of [sidebarMenu, workspaceSwitcher, turnTreeActions, figureTab]) {
    assert.equal(source.includes('<FloatingActionMenu'), true)
  }

  assert.equal(sidebarMenu.includes('data-conversation-actions-menu'), true)
  assert.equal(turnTreeActions.includes('data-turn-tree-context-menu'), true)
  assert.equal(workspaceSwitcher.includes('data-workspace-context-menu'), true)
  assert.equal(figureTab.includes('data-figure-export-menu'), true)
})

test('dropdown components share option surface, search, empty state, and positioning internals', () => {
  const sharedStyles = read('src/components/ui/dropdownShared.js')
  const floating = read('src/composables/useFloatingDropdown.js')
  const header = read('src/components/ui/HeaderDropdown.vue')
  const multi = read('src/components/ui/MultiSelectDropdown.vue')
  const model = read('src/components/ui/ModelSelector.vue')

  assert.equal(sharedStyles.includes('dropdownSurfaceClass'), true)
  assert.equal(sharedStyles.includes('dropdownOptionStyle'), true)
  assert.equal(sharedStyles.includes('dropdownSearchInputClass'), true)
  assert.equal(sharedStyles.includes('dropdownEmptyClass'), true)
  assert.equal(floating.includes('updateFloatingDropdownPosition'), true)

  for (const source of [header, multi, model]) {
    assert.equal(source.includes('dropdownSurfaceClass'), true)
    assert.equal(source.includes('dropdownSearchInputClass'), true)
    assert.equal(source.includes('dropdownOptionStyle'), true)
  }

  assert.equal(model.includes("emit('model-changed'"), true)
  assert.equal(model.includes('backendSearch'), true)
  assert.equal(model.includes('provider'), true)
})

test('audited components avoid stale hardcoded foreground and overlay utilities', () => {
  const componentRoot = resolve(process.cwd(), 'src/components')
  const sources = walkVueFiles(componentRoot).map((filePath) => [filePath, readFileSync(filePath, 'utf-8')])
  const offenders = sources
    .filter(([filePath]) => !filePath.endsWith('ui/FloatingActionMenu.vue'))
    .filter(([, source]) => source.includes('text-white') || source.includes('bg-black/25'))
    .map(([filePath]) => filePath)

  assert.deepEqual(offenders, [])

  const styleSource = read('src/style.css')
  assert.equal(styleSource.includes('@apply inline-flex items-center justify-center font-medium rounded-lg focus:outline-none text-white'), false)
  assert.equal(styleSource.includes('color: var(--color-on-accent);'), true)

  const appearance = read('src/components/modals/tabs/AppearanceTab.vue')
  assert.equal(appearance.includes("color-mix(in srgb, white"), false)
  assert.equal(appearance.includes("color-mix(in srgb, black"), false)
  assert.equal(appearance.includes('theme-preview-surface'), true)
})

test('large components are split into workflow components and composables', () => {
  const workspaceTab = read('src/components/modals/tabs/WorkspaceTab.vue')
  const chatInput = read('src/components/chat/ChatInput.vue')
  const chatHistory = read('src/components/chat/ChatHistory.vue')
  const tableTab = read('src/components/analysis/TableTab.vue')
  const sidebar = read('src/components/layout/UnifiedSidebar.vue')

  for (const componentName of [
    'WorkspaceListPanel',
    'WorkspaceContextSection',
    'WorkspaceDatasetSection',
    'WorkspaceRuntimeReadiness',
  ]) {
    assert.equal(workspaceTab.includes(componentName), true)
  }
  assert.equal(workspaceTab.includes('useWorkspaceDatasets'), true)

  for (const componentName of ['ChatAttachmentTray', 'ChatComposerActions']) {
    assert.equal(chatInput.includes(componentName), true)
  }
  assert.equal(chatInput.includes('useChatAttachments'), true)
  assert.equal(chatInput.includes('useChatAutocomplete'), true)
  assert.equal(chatInput.includes('useVoiceInput'), true)

  for (const componentName of ['ChatUserMessage', 'ChatAssistantMessage']) {
    assert.equal(chatHistory.includes(componentName), true)
  }
  assert.equal(chatHistory.includes('useChatScrollFollow'), true)

  for (const componentName of ['TableToolbar', 'TableGridShell', 'TableEmptyState']) {
    assert.equal(tableTab.includes(componentName), true)
  }
  assert.equal(tableTab.includes('useTableArtifacts'), true)

  for (const componentName of ['SidebarPrimaryNav', 'SidebarWorkspaceConversations', 'SidebarFooter']) {
    assert.equal(sidebar.includes(componentName), true)
  }
  assert.equal(sidebar.includes('useSidebarConversations'), true)
})

test('frontend ui audit reflects corrected stale-code findings', () => {
  const audit = read('../docs/frontend-ui-audit.md')
  const workspaceSwitcher = read('src/components/WorkspaceSwitcher.vue')
  const duplicateAssignments = workspaceSwitcher.match(/isRenamingWorkspace\.value = true/g) || []

  assert.equal(duplicateAssignments.length, 1)
  assert.equal(audit.includes('assigns `isRenamingWorkspace.value = true` twice'), false)
  assert.equal(audit.includes('WorkspaceSwitcher.vue was re-checked'), true)
})
