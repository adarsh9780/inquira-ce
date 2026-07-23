import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('app motion primitives share intentional timing and reduced-motion behavior', () => {
  const styles = read('src/style.css')

  assert.match(styles, /--motion-duration-popover-enter:\s*180ms/)
  assert.match(styles, /--motion-duration-popover-leave:\s*140ms/)
  assert.match(styles, /\.motion-popover-enter-from[\s\S]*translate3d\(0, var\(--motion-popover-y\), 0\)/)
  assert.match(styles, /\.motion-disclosure[\s\S]*grid-template-rows:\s*0fr/)
  assert.match(styles, /\.motion-disclosure-open[\s\S]*grid-template-rows:\s*1fr/)
  assert.match(styles, /\.motion-toast-enter-from[\s\S]*translate3d/)
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)[\s\S]*transition-duration:\s*0\.01ms !important/)
})

test('floating overlays animate from their anchor and are positioned before enter', () => {
  const headerDropdown = read('src/components/ui/HeaderDropdown.vue')
  const modelSelector = read('src/components/ui/ModelSelector.vue')
  const floatingMenu = read('src/components/ui/FloatingActionMenu.vue')
  const floatingPosition = read('src/composables/useFloatingDropdown.js')
  const sharedDropdown = read('src/components/ui/dropdownShared.js')

  for (const source of [headerDropdown]) {
    assert.match(source, /<Transition name="motion-popover" @before-enter="prepareFloatingPosition">/)
    assert.match(source, /function prepareFloatingPosition\(element\)/)
    assert.doesNotMatch(source, /duration-100 ease-out|duration-75 ease-in/)
  }

  assert.match(sharedDropdown, /motion-popover-surface/)
  assert.match(floatingPosition, /'--motion-popover-origin'/)
  assert.match(floatingPosition, /'--motion-popover-y'/)
  assert.match(modelSelector, /motion-popover-from-bottom/)
  assert.match(floatingMenu, /@before-enter="prepareMenuEnter"/)
  assert.match(floatingMenu, /element\.style\.left/)
})

test('dialogs, compact panels, disclosures, and toasts all have exit motion', () => {
  const modalPaths = [
    'src/components/modals/SettingsModal.vue',
    'src/components/modals/ConfirmationModal.vue',
    'src/components/modals/KeyboardShortcutsModal.vue',
    'src/components/modals/TermsModal.vue',
    'src/components/modals/CommandPaletteModal.vue',
    'src/components/modals/ConversationTreeRulesModal.vue',
    'src/components/chat/TurnTreeNodeActions.vue',
  ]
  for (const path of modalPaths) {
    const source = read(path)
    assert.match(source, /dialog-fade-leave-active dialog-pop-leave-active/, path)
    assert.match(source, /dialog-fade-leave-to dialog-pop-leave-to/, path)
  }

  const popoverPaths = [
    'src/components/layout/StatusBar.vue',
    'src/components/layout/UnifiedSidebar.vue',
    'src/components/analysis/table/DataTable.vue',
    'src/components/chat/ChatInput.vue',
  ]
  for (const path of popoverPaths) {
    assert.match(read(path), /<Transition name="motion-popover"/, path)
  }

  assert.match(read('src/components/chat/ToolOutputPreview.vue'), /motion-disclosure-content/)
  assert.match(read('src/components/ui/ToastContainer.vue'), /<TransitionGroup name="motion-toast"/)
})

test('openable detail views avoid native and fixed max-height snapping', () => {
  const detailPaths = [
    'src/components/modals/tabs/LLMSettingsTab.vue',
    'src/components/modals/tabs/WorkspaceTab.vue',
    'src/components/modals/tabs/WorkspaceAIConfigSection.vue',
    'src/components/chat/ChatHistory.vue',
    'src/components/chat/ToolOutputPreview.vue',
  ]

  for (const path of detailPaths) {
    const source = read(path)
    assert.doesNotMatch(source, /<details|<\/details>/, path)
  }
  assert.doesNotMatch(read('src/components/modals/tabs/LLMSettingsTab.vue'), /maxHeight:\s*showAdvanced/)
})
