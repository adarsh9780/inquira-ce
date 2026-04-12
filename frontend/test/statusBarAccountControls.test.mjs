import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar account name opens sidebar, workspace/schema toggle is next to name', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  // Account name button toggles sidebar (not dropdown)
  assert.equal(statusBarSource.includes('@click.stop="toggleSidebarFromStatusBar"'), true)
  assert.equal(statusBarSource.includes('toggleAccountMenu'), false)
  assert.equal(statusBarSource.includes('accountMenuRef'), false)
  assert.equal(statusBarSource.includes('aria-label="Open sidebar"'), true)

  // No dropdown-related elements
  assert.equal(statusBarSource.includes('Open account menu'), false)
  assert.equal(statusBarSource.includes('Close account menu'), false)
  assert.equal(statusBarSource.includes('aria-label="Toggle account menu"'), false)
  assert.equal(statusBarSource.includes('ChevronUpIcon'), false)
  assert.equal(statusBarSource.includes('ChevronDownIcon'), false)

  // Sidebar toggle still exists via status bar
  assert.equal(statusBarSource.includes('toggleSidebarFromStatusBar'), true)
  assert.equal(statusBarSource.includes('Show sidebar (Cmd/Ctrl+B)'), true)
  assert.equal(statusBarSource.includes('Hide sidebar (Cmd/Ctrl+B)'), true)
  assert.equal(statusBarSource.includes('ChevronRightIcon'), true)
  assert.equal(statusBarSource.includes('ChevronLeftIcon'), true)
  assert.equal(statusBarSource.includes('appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)'), true)
  assert.equal(statusBarSource.includes('function openSidebar() {'), false)

  // Workspace/Schema toggle is next to account name in left section
  assert.equal(statusBarSource.includes('switchToWorkspace'), true)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), true)
  assert.equal(statusBarSource.includes('FolderOpenIcon'), true)
  assert.equal(statusBarSource.includes('DocumentTextIcon'), true)

  // Check Workspace/Schema toggle appears before Kernel Status in the left section
  const accountNameIndex = statusBarSource.indexOf('Open sidebar')
  const workspaceToggleIndex = statusBarSource.indexOf('switchToWorkspace')
  const kernelStatusIndex = statusBarSource.indexOf('<!-- Kernel Status -->')
  assert.equal(workspaceToggleIndex > accountNameIndex && workspaceToggleIndex < kernelStatusIndex, true)

  // Account display label
  assert.equal(statusBarSource.includes('accountDisplayLabel'), true)
  assert.equal(statusBarSource.includes("if (!value.includes(' '))"), true)

  // Editor position still exists
  assert.equal(statusBarSource.includes('Ln {{ appStore.editorLine }}'), true)
  assert.equal(statusBarSource.includes('Col {{ appStore.editorCol }}'), true)

  // Data Focus and Terminal toggles
  assert.equal(statusBarSource.includes('Enter data focus mode (Cmd/Ctrl+Shift+D)'), true)
  assert.equal(statusBarSource.includes('Exit data focus mode (Cmd/Ctrl+Shift+D)'), true)
  assert.equal(statusBarSource.includes('Toggle terminal panel (Cmd/Ctrl+J)'), true)
  assert.equal(statusBarSource.includes('ViewColumnsIcon'), true)
  assert.equal(statusBarSource.includes('CommandLineIcon'), true)

  // Right section doesn't have Workspace/Schema toggle anymore
  assert.equal(statusBarSource.includes('Right Section: Editor Toggle, Data Focus, Terminal & Version'), false)
  assert.equal(statusBarSource.includes('Right Section: Data Focus, Terminal & Version'), true)

  // Settings and Terms in sidebar (CE: no logout)
  assert.equal(sidebarSource.includes('CogIcon'), true)
  // Terms uses ScaleIcon (balance/legal icon), not DocumentIcon
  assert.equal(sidebarSource.includes('ScaleIcon'), true)
  assert.equal(sidebarSource.includes('openSettings'), true)
  assert.equal(sidebarSource.includes('openTerms'), true)
  assert.equal(sidebarSource.includes('isTermsDialogOpen'), true)

  // CE: auth/logout elements removed from sidebar
  assert.equal(sidebarSource.includes('ArrowRightOnRectangleIcon'), false)
  assert.equal(sidebarSource.includes('promptLogout'), false)
  assert.equal(sidebarSource.includes('isLogoutConfirmOpen'), false)
  // ConfirmationModal is used for delete confirmations (new feature in redesign)
  assert.equal(sidebarSource.includes('ConfirmationModal'), true)

  // Sidebar no longer has Workspace/Schema toggle
  assert.equal(sidebarSource.includes('handleTabClick'), false)
  assert.equal(sidebarSource.includes('DocumentTextIcon'), false) // In schema editor toggle context

  // StatusBar no longer has Settings/Confirmation modal directly
  assert.equal(statusBarSource.includes('<SettingsModal'), false)
  assert.equal(statusBarSource.includes('<ConfirmationModal'), false)
  assert.equal(statusBarSource.includes('const isTermsDialogOpen = ref(false)'), false)
  assert.equal(statusBarSource.includes("const termsMarkdown = ref('')"), false)
  assert.equal(statusBarSource.includes('await apiService.v1GetTermsAndConditions()'), false)
  assert.equal(statusBarSource.includes('Loading terms...'), false)
  assert.equal(statusBarSource.includes('terms-markdown-content'), false)
  assert.equal(statusBarSource.includes('backdrop-blur-[1.5px]'), false)
})

test('sidebar has settings and terms buttons (CE: no logout)', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  // Settings button in sidebar
  assert.equal(sidebarSource.includes('@click="openSettings'), true)
  assert.equal(sidebarSource.includes('title="Settings"'), true)

  // Terms & Conditions button in sidebar
  assert.equal(sidebarSource.includes('@click="openTerms'), true)
  assert.equal(sidebarSource.includes('title="Terms & Conditions"'), true)

  // CE: logout removed — no auth needed
  assert.equal(sidebarSource.includes('@click="promptLogout'), false)
  assert.equal(sidebarSource.includes('title="Logout"'), false)
  assert.equal(sidebarSource.includes('Confirm Logout'), false)

  // Terms dialog
  assert.equal(sidebarSource.includes('Terms & Conditions'), true)
  assert.equal(sidebarSource.includes('Last updated:'), true)
})

test('workspace/schema toggle buttons use correct icons and styling', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )

  // Workspace button uses FolderOpenIcon
  assert.ok(statusBarSource.includes('FolderOpenIcon'))
  assert.ok(statusBarSource.includes("title=\"'Switch to Workspace'\""))

  // Schema button uses DocumentTextIcon
  assert.ok(statusBarSource.includes('DocumentTextIcon'))
  assert.ok(statusBarSource.includes("title=\"'Switch to Schema Editor'\""))

  // Active tab styling now uses CSS variables
  assert.ok(statusBarSource.includes("appStore.activeTab === 'workspace'"))
  assert.ok(statusBarSource.includes("appStore.activeTab === 'schema-editor'"))
  // New design uses CSS variables instead of hardcoded blue
  assert.ok(statusBarSource.includes("text-[var(--color-accent)] font-medium"))
})
