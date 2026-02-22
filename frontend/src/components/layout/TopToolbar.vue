<template>
  <header class="bg-gradient-to-r from-white to-gray-50 border-b border-pastel-500 px-4 sm:px-9 py-3 sm:py-4 shadow-sm">
    <div class="flex items-center justify-between">
      <!-- Left Section: Logo & Title -->
      <div class="flex items-center space-x-3 flex-shrink-0">
        <img :src="logo" alt="Inquira Logo" class="w-10 h-10 rounded-lg" />
        <div class="hidden sm:block">
          <h1 class="text-lg font-bold text-primary-900">Inquira</h1>
          <p class="text-xs text-primary-600">LLM-Powered Data Analysis</p>
        </div>
      </div>

      <!-- Center Section: Dataset Switcher (Prominent) -->
      <div class="flex-1 flex justify-center px-4 items-center space-x-3">
        <WorkspaceSwitcher />
        <DatasetSwitcher @open-settings="openSettings" />
      </div>

      <!-- Right Section: User Controls Group -->
      <div class="flex items-center space-x-3 flex-shrink-0">
        <!-- Configuration Status Dot -->
        <div class="relative group">
          <div
            class="w-3 h-3 rounded-full cursor-help transition-all duration-200 hover:scale-110"
            :class="getStatusDotClasses"
            title="Click to open Settings"
            @click="openSettings()"
          ></div>

          <!-- Hover Tooltip -->
          <div class="absolute top-full mt-2 right-0 w-80 bg-white rounded-lg shadow-lg border border-pastel-300 p-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <div class="text-sm font-semibold text-primary-900 mb-3">Configuration Status</div>
            <div class="grid grid-cols-2 gap-3 max-w-md">
              <!-- Data File Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.hasDataFile ? 'border-success/20 bg-success/10' : 'border-gray-200 bg-gray-50'">
                <div class="w-2 h-2 rounded-full" :class="appStore.hasDataFile ? 'bg-success' : 'bg-gray-400'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.hasDataFile ? 'text-primary' : 'text-gray-600'">Data File</p>
                  <p class="text-xs" :class="appStore.hasDataFile ? 'text-primary' : 'text-gray-500'">{{ appStore.hasDataFile ? 'Set' : 'Optional' }}</p>
                </div>
              </div>

              <!-- Schema File Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.hasSchemaFile ? 'border-success/20 bg-success/10' : 'border-gray-200 bg-gray-50'">
                <div class="w-2 h-2 rounded-full" :class="appStore.hasSchemaFile ? 'bg-success' : 'bg-gray-400'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.hasSchemaFile ? 'text-primary' : 'text-gray-600'">Schema File</p>
                  <p class="text-xs" :class="appStore.hasSchemaFile ? 'text-primary' : 'text-gray-500'">{{ appStore.hasSchemaFile ? 'Set' : 'Optional' }}</p>
                </div>
              </div>

              <!-- Schema Context Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.schemaContext ? 'border-accent/20 bg-accent/10' : 'border-gray-200 bg-gray-50'">
                <div class="w-2 h-2 rounded-full" :class="appStore.schemaContext ? 'bg-accent' : 'bg-gray-400'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.schemaContext ? 'text-primary' : 'text-gray-600'">Schema Context</p>
                  <p class="text-xs" :class="appStore.schemaContext ? 'text-primary' : 'text-gray-500'">{{ appStore.schemaContext ? 'Set' : 'Optional' }}</p>
                </div>
              </div>

              <!-- API Key Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.apiKeyConfigured ? 'border-success/20 bg-success/10' : 'border-error/20 bg-error/10'">
                <div class="w-2 h-2 rounded-full" :class="appStore.apiKeyConfigured ? 'bg-success' : 'bg-error'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.apiKeyConfigured ? 'text-primary' : 'text-error'">API Key</p>
                  <p class="text-xs" :class="appStore.apiKeyConfigured ? 'text-primary' : 'text-error'">{{ appStore.apiKeyConfigured ? 'Configured' : 'Required' }}</p>
                </div>
              </div>

              <!-- WebSocket Connection Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="isWebSocketConnected ? 'border-success/20 bg-success/10' : 'border-error/20 bg-error/10'">
                <div class="w-2 h-2 rounded-full" :class="isWebSocketConnected ? 'bg-success' : 'bg-error'"></div>
                <div>
                  <p class="text-xs font-medium" :class="isWebSocketConnected ? 'text-primary' : 'text-error'">Backend Connection</p>
                  <p class="text-xs" :class="isWebSocketConnected ? 'text-primary' : 'text-error'">{{ isWebSocketConnected ? 'Connected' : 'Disconnected' }}</p>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-3 border-t border-pastel-300">
              <p class="text-xs text-primary-600 text-center">Click to open Settings</p>
            </div>
          </div>
        </div>

        <!-- Preview Actions removed; use Preview tab -->

        <!-- User Menu Dropdown -->
        <div class="relative" v-if="authStore.isAuthenticated">
          <button
            @click="toggleUserMenu"
            class="user-menu-button flex items-center space-x-2 px-4 py-3 text-sm font-medium text-primary bg-gray-50 hover:bg-gray-100 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-sm"
            :class="{ 'bg-gray-100 shadow-md': isUserMenuOpen }"
            :title="`Logged in as ${authStore.username}`"
          >
            <div class="w-7 h-7 bg-gradient-to-br from-primary-600 to-accent-500 rounded-full flex items-center justify-center">
              <UserIcon class="h-3.5 w-3.5 text-white" />
            </div>
            <div class="hidden md:block text-left">
              <p class="text-sm font-semibold text-primary">{{ authStore.username }}</p>
              <p class="text-xs text-gray-500">{{ authStore.planLabel }} plan</p>
            </div>
            <ChevronDownIcon class="h-3.5 w-3.5 text-gray-400" />
          </button>

          <!-- Dropdown Menu -->
          <div
            v-if="isUserMenuOpen"
            class="user-menu-dropdown absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-50 border border-pastel-200"
            @click.stop
          >
            <!-- User Info Header -->
            <div class="px-4 py-3 border-b border-pastel-300 bg-pastel-500 rounded-t-lg">
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 bg-gradient-to-br from-primary-700 to-accent-600 rounded-full flex items-center justify-center">
                  <UserIcon class="h-4 w-4 text-white" />
                </div>
                <div>
                  <p class="text-sm font-semibold text-white">{{ authStore.username }}</p>
                  <p class="text-xs text-pastel-100">{{ authStore.planLabel }} plan</p>
                </div>
              </div>
            </div>

            <div class="py-1">
              <button
                @click="openSettings()"
                class="flex items-center w-full px-4 py-2.5 text-sm text-primary hover:bg-gray-50 hover:text-primary transition-colors"
              >
                <CogIcon class="h-4 w-4 mr-3 text-gray-500" />
                Settings
              </button>

              <button
                @click="openShortcuts"
                class="flex items-center w-full px-4 py-2.5 text-sm text-primary hover:bg-gray-50 hover:text-primary transition-colors"
              >
                <CommandLineIcon class="h-4 w-4 mr-3 text-gray-500" />
                Shortcuts
              </button>

              <button
                @click="openTerms"
                class="flex items-center w-full px-4 py-2.5 text-sm text-primary hover:bg-gray-50 hover:text-primary transition-colors"
              >
                <DocumentTextIcon class="h-4 w-4 mr-3 text-gray-500" />
                Terms &amp; Conditions
              </button>

              <div class="border-t border-pastel-200 my-1"></div>

              <button
                @click="handleLogout"
                class="flex items-center w-full px-4 py-2.5 text-sm text-error hover:bg-error/10 hover:text-error transition-colors"
              >
                <ArrowRightOnRectangleIcon class="h-4 w-4 mr-3" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>


  <!-- Settings Modal -->
  <SettingsModal
    :is-open="isSettingsOpen"
    :initial-tab="settingsInitialTab"
    @close="closeSettings"
  />

  

  <!-- Shortcuts Modal -->
  <ShortcutsModal
    :is-open="isShortcutsOpen"
    @close="closeShortcuts"
  />

  <!-- Logout Confirmation Modal -->
  <ConfirmationModal
    :is-open="isLogoutConfirmOpen"
    title="Confirm Logout"
    :message="`Are you sure you want to log out, ${authStore.username}?`"
    confirm-text="Log Out"
    cancel-text="Cancel"
    @close="cancelLogout"
    @confirm="confirmLogout"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { settingsWebSocket } from '../../services/websocketService'
import SettingsModal from '../modals/SettingsModal.vue'
// PreviewModal removed; use in-panel tabs instead
import ShortcutsModal from '../modals/ShortcutsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import { CogIcon, ArrowRightOnRectangleIcon, UserIcon, CommandLineIcon, ChevronDownIcon, DocumentTextIcon } from '@heroicons/vue/24/outline'
import logo from '../../assets/favicon.svg'
import DatasetSwitcher from '../DatasetSwitcher.vue'
import WorkspaceSwitcher from '../WorkspaceSwitcher.vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api') // 'api' | 'data' | 'account'
// const isNewPreviewOpen = ref(false) // removed
const isUserMenuOpen = ref(false)
const isShortcutsOpen = ref(false)
const isLogoutConfirmOpen = ref(false)
const isWebSocketConnected = ref(false)

// Computed property to check if configuration is complete
const isConfigurationComplete = computed(() => {
  return appStore.apiKeyConfigured && appStore.hasDataFile && isWebSocketConnected.value
})

// Computed property for status dot classes with blinking animation
const getStatusDotClasses = computed(() => {
  if (isConfigurationComplete.value) {
    return 'bg-success shadow-success/20 shadow-sm'
  } else {
    // Check if WebSocket is the issue
    if (!isWebSocketConnected.value) {
      return 'bg-error shadow-error/20 shadow-sm animate-pulse'
    } else {
      return 'bg-gray-400 shadow-gray-200 shadow-sm'
    }
  }
})

// Auto-show shortcuts modal after page load
function autoShowShortcutsModal() {
  // Only show if user is authenticated and hasn't opted out
  if (authStore.isAuthenticated) {
    if (!appStore.hideShortcutsModal) {
      // Show modal after a short delay to let the page load first
      setTimeout(() => {
        isShortcutsOpen.value = true
      }, 1500) // 1.5 seconds delay
    }
  }
}

// Setup WebSocket connection monitoring
function setupWebSocketMonitoring() {
  // Monitor connection status
  const unsubscribe = settingsWebSocket.onConnection((connected) => {
    isWebSocketConnected.value = connected
    console.debug('WebSocket connection status changed:', connected)
  })

  // Set initial status
  isWebSocketConnected.value = settingsWebSocket.isConnected

  // Cleanup subscription when component unmounts
  onUnmounted(() => {
    if (typeof unsubscribe === 'function') unsubscribe()
  })
}

// Call auto-show when component is mounted
onMounted(() => {
  autoShowShortcutsModal()
  setupWebSocketMonitoring()
})

function openSettings(tab = 'api') {
  const normalizedTab = typeof tab === 'string' ? tab.toLowerCase() : 'api'
  settingsInitialTab.value = ['api', 'data', 'account'].includes(normalizedTab) ? normalizedTab : 'api'
  isSettingsOpen.value = true
  isUserMenuOpen.value = false // Close dropdown when opening settings
}

function closeSettings() {
  isSettingsOpen.value = false
  settingsInitialTab.value = 'api' // Reset to default
}


// openNewPreview/closeNewPreview removed

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

function openShortcuts() {
  isShortcutsOpen.value = true
  isUserMenuOpen.value = false // Close dropdown when opening shortcuts
}

function openTerms() {
  isUserMenuOpen.value = false
  window.open('/terms-and-conditions.html', '_blank', 'noopener')
}


// Preview modal removed; use in-panel Preview tab
// switchPreviewTab removed (Preview modal deprecated)

function closeShortcuts() {
  isShortcutsOpen.value = false
}

function handleLogout() {
  // Show custom confirmation modal
  isLogoutConfirmOpen.value = true
  isUserMenuOpen.value = false // Close dropdown when opening logout confirmation
}

async function confirmLogout() {
  isLogoutConfirmOpen.value = false

  try {
    await authStore.logout()
    // The auth store will handle clearing the authentication state
    // and the UI will update automatically due to reactivity
  } catch (error) {
    console.error('Logout failed:', error)
  }
}

function cancelLogout() {
  isLogoutConfirmOpen.value = false
}

// Global shortcut helper functions
function focusChatInput() {
  // Find and focus the chat input textarea
  const chatInput = document.querySelector('textarea[placeholder*="Ask a question"]')
  if (chatInput) {
    chatInput.focus()
    // Scroll into view if needed
    chatInput.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function focusCodeEditor() {
  // Find and focus the code editor
  const codeEditor = document.querySelector('.cm-editor')
  if (codeEditor) {
    codeEditor.focus()
    // Scroll into view if needed
    codeEditor.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function focusCodeEditorAtEnd() {
  // Find and focus the code editor at the end of the current line
  const codeEditor = document.querySelector('.cm-editor')
  if (codeEditor) {
    codeEditor.focus()
    // Scroll into view if needed
    codeEditor.scrollIntoView({ behavior: 'smooth', block: 'center' })

    // Try to move cursor to end of line (this may need adjustment based on CodeMirror API)
    try {
      // For CodeMirror, we can try to dispatch an End key event
      const endKeyEvent = new KeyboardEvent('keydown', {
        key: 'End',
        code: 'End',
        keyCode: 35,
        which: 35,
        bubbles: true,
        cancelable: true
      })
      codeEditor.dispatchEvent(endKeyEvent)
    } catch (error) {
      // Fallback: just focus the editor
      console.debug('Could not move cursor to end of line:', error)
    }
  }
}

function runCode() {
  // Trigger code execution
  // This could be a button click or direct function call
  const runButton = document.querySelector('button[title*="Run"], button[title*="Execute"]')
  if (runButton) {
    runButton.click()
  } else {
    // Fallback: try to find any run-related button
    const buttons = document.querySelectorAll('button')
    for (const button of buttons) {
      if (button.textContent.toLowerCase().includes('run') ||
          button.textContent.toLowerCase().includes('execute') ||
          button.title.toLowerCase().includes('run')) {
        button.click()
        break
      }
    }
  }
}

function downloadCode() {
  try {
    // Get the Python code from the app store
    const code = appStore.pythonFileContent || '# No code in editor'

    // Create a blob with the code
    const blob = new Blob([code], { type: 'text/plain' })

    // Create a download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
    link.download = `python_code_${timestamp}.py`

    // Trigger download
    document.body.appendChild(link)
    link.click()

    // Clean up
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    console.debug('Python code downloaded successfully')
  } catch (error) {
    console.error('Failed to download code:', error)
  }
}


// Helper function to check if user is in a regular input field (not CodeMirror)
function isInInputField() {
  const activeElement = document.activeElement
  const tagName = activeElement?.tagName?.toLowerCase()

  // Treat CodeMirror as an input context (disable global shortcuts while editing)
  if (activeElement?.closest && activeElement.closest('.cm-editor')) {
    return true
  }

  // Standard inputs and textareas
  if (tagName === 'input' || tagName === 'textarea') {
    return true
  }

  // Any other contenteditable element
  if (activeElement?.contentEditable === 'true') {
    return true
  }

  return false
}

// Keyboard shortcuts - Caps Lock + key combinations for cross-platform compatibility
function handleKeydown(event) {

  // Don't handle Enter key - let it go to editors
  if (event.key === 'Enter') {
    return
  }

  // Caps Lock handling removed - now using Ctrl+Shift combinations

  // Handle Escape key to exit input fields and close modals/dropdowns
  if (event.key === 'Escape') {
    console.debug('Escape pressed')

    // Escape key handling for modal/dropdown closing

    // Close modals in priority order (most recent first)
    if (isLogoutConfirmOpen.value) {
      console.debug('Closing logout confirmation modal')
      cancelLogout()
      event.preventDefault()
      return
    }

    if (isShortcutsOpen.value) {
      console.debug('Closing shortcuts modal')
      closeShortcuts()
      event.preventDefault()
      return
    }

    // Preview modal removed

    if (isSettingsOpen.value) {
      console.debug('Closing settings modal')
      closeSettings()
      event.preventDefault()
      return
    }

    // Close dropdowns
    if (isUserMenuOpen.value) {
      isUserMenuOpen.value = false
      event.preventDefault()
      return
    }

    // Exit input fields
    const activeElement = document.activeElement
    if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA' || activeElement.contentEditable === 'true')) {
      activeElement.blur()
      event.preventDefault()
      return
    }
  }

  // Only handle shortcuts when not in input fields
  if (isInInputField()) {
    return
  }

  // Single-letter shortcuts (no modifier keys needed) - only when NOT in input fields
  if (!event.ctrlKey && !event.altKey && !event.metaKey && !event.shiftKey) {
    const key = event.key.toLowerCase()
    console.debug('Processing single-letter shortcut:', key)

    switch (key) {
      case 'c':
        console.debug('c: Switching to code tab')
        event.preventDefault()
        appStore.setActiveTab('code')
        break
      case 't':
        console.debug('t: Switching to table tab')
        event.preventDefault()
        appStore.setActiveTab('table')
        break
      case 'i':
        console.debug('i: Focusing chat input')
        event.preventDefault()
        focusChatInput()
        break
      case 'w':
        console.debug('w: Focusing code editor at end')
        event.preventDefault()
        focusCodeEditorAtEnd()
        break
      case 'r':
        console.debug('r: Running code')
        event.preventDefault()
        runCode()
        break
      case 'g':
        console.debug('g: Downloading Python code')
        event.preventDefault()
        downloadCode()
        break
      case 'h':
        // 'h' toggles Chat overlay
        console.debug('h: Toggle chat overlay')
        event.preventDefault()
        appStore.toggleChatOverlay()
        if (appStore.isChatOverlayOpen) {
          focusChatInput()
        }
        break
      case 'f':
        console.debug('f: Switching to figure tab')
        event.preventDefault()
        appStore.setActiveTab('figure')
        break
      case 'v':
        console.debug('v: Switching to preview tab')
        event.preventDefault()
        appStore.setActiveTab('preview')
        break
      case 'e':
        console.debug('e: Switching to schema editor tab')
        event.preventDefault()
        appStore.setActiveTab('schema-editor')
        break
      case 'o':
        console.debug('o: Switching to terminal tab')
        event.preventDefault()
        appStore.setActiveTab('terminal')
        break
      case ',':
        console.debug(',: Opening settings')
        event.preventDefault()
        openSettings()
        break
      case 'k':
        console.debug('k: Opening shortcuts')
        event.preventDefault()
        openShortcuts()
        break
      // Modal shortcuts removed; use v/e for tabs
      case 'n':
        console.debug('n: Toggle notebook mode')
        event.preventDefault()
        // This will be handled by the code tab component
        // We need to emit an event or use a global method
        const notebookToggle = document.querySelector('button[title*="Notebook Mode"]')
        if (notebookToggle) {
          notebookToggle.click()
        }
        break
      default:
        // Not a shortcut key, allow normal typing (don't prevent default)
        console.debug('Not a shortcut key, allowing normal typing')
        return
    }
  }
}



// Event listeners setup

// Add keyboard event listener
document.addEventListener('keydown', handleKeydown)

// Close user menu when clicking outside
document.addEventListener('click', (event) => {
  const userMenu = document.querySelector('.user-menu-dropdown')
  const userButton = document.querySelector('.user-menu-button')

  if (isUserMenuOpen.value && userMenu && userButton &&
      !userMenu.contains(event.target) && !userButton.contains(event.target)) {
    isUserMenuOpen.value = false
  }
})
</script>

<style scoped>
/* Custom urgent blinking animation for connection issues */
@keyframes urgentBlink {
  0%, 50% {
    opacity: 1;
    transform: scale(1);
  }
  25%, 75% {
    opacity: 0.3;
    transform: scale(0.95);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-pulse {
  animation: urgentBlink 1.5s ease-in-out infinite;
}

/* Ensure the tooltip appears above other elements */
.group:hover .absolute {
  z-index: 9999;
}
</style>
