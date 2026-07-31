import { onMounted, onUnmounted, type Ref } from 'vue'
import { matchShortcut } from '../utils/keyboardShortcuts'
import { useUiStore } from '../stores/uiStore'
import { useWorkspaceStore } from '../stores/workspaceStore'

export function useGlobalShortcuts(isAuthenticated: Ref<boolean>, openDatasetPicker: () => void) {
  const ui = useUiStore()
  const workspace = useWorkspaceStore()

  function handleGlobalShortcuts(event: KeyboardEvent) {
    if (!isAuthenticated.value || event.defaultPrevented || event.repeat) return
    if (!(event.metaKey || event.ctrlKey) || event.altKey) return

    const actions: Array<[string, () => void]> = [
      ['conversation-tree', () => ui.setActiveTab('conversation-tree')],
      ['conversation-switcher', () => {
        if (workspace.hasWorkspace) ui.toggleConversationSwitcher()
      }],
      ['settings', () => ui.openSettings('setup')],
      ['sidebar', () => ui.setSidebarCollapsed(!ui.isSidebarCollapsed)],
      ['schema', () => ui.setActiveTab('schema-editor')],
      ['dataset-import', openDatasetPicker],
      ['terminal', () => ui.toggleTerminal()],
    ]
    const action = actions.find(([shortcut]) => matchShortcut(event, shortcut))
    if (!action) return
    event.preventDefault()
    action[1]()
  }

  onMounted(() => document.addEventListener('keydown', handleGlobalShortcuts))
  onUnmounted(() => document.removeEventListener('keydown', handleGlobalShortcuts))

  return { handleGlobalShortcuts }
}
