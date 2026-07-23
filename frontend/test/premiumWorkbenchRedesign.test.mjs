import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')

test('the workbench exposes one contextual shell and direct evidence destinations', () => {
  const panel = read('src/components/layout/RightPanel.vue')
  const contextBar = read('src/components/layout/WorkspaceContextBar.vue')
  const leftPane = read('src/components/layout/WorkspaceLeftPane.vue')
  const rightPane = read('src/components/layout/WorkspaceRightPane.vue')
  const statusBar = read('src/components/layout/StatusBar.vue')
  const statusTemplate = statusBar.split('</template>')[0]

  assert.match(panel, /<WorkspaceContextBar/)
  assert.match(contextBar, /data-workspace-context-bar/)
  assert.match(contextBar, /data-action="add-data"/)
  assert.match(contextBar, /v-if="appStore\.hasWorkspace"[\s\S]*data-workspace-status/)
  assert.match(contextBar, /:aria-label="[^"]*Add a data source[^"]*"/)
  assert.match(leftPane, /v-if="appStore\.workspacePane === 'chat' && appStore\.workspaceReadiness\.ready"/)
  assert.match(rightPane, /<SegmentedControl/)
  assert.doesNotMatch(rightPane, /v-model="selectedCategory"[\s\S]*<HeaderDropdown/)
  assert.doesNotMatch(statusTemplate, /data-workspace-switcher/)
  assert.doesNotMatch(statusTemplate, /data-websocket-status/)
  assert.doesNotMatch(statusTemplate, />\s*Inquira v\{\{ uiVersion \}\}/)
  assert.match(statusTemplate, /v-if="authStore\.isAuthenticated && hasTokenUsage"/)
})

test('all primary add-data entry points use the native connection flow contract', () => {
  const app = read('src/App.vue')
  const store = read('src/stores/appStore.js')
  const chat = read('src/components/chat/ChatTab.vue')
  const palette = read('src/components/modals/CommandPaletteModal.vue')
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.match(store, /const connectionFlowRequestId = ref\(0\)/)
  assert.match(store, /function openDataConnectionFlow\(/)
  assert.match(app, /appStore\.openDataConnectionFlow\(\)/)
  assert.match(chat, /appStore\.openDataConnectionFlow\(\)/)
  assert.match(palette, /appStore\.openDataConnectionFlow\(\)/)
  assert.match(setup, /appStore\.openDataConnectionFlow\(\)/)
  assert.match(workspace, /const handledConnectionFlowRequestIds = new WeakMap\(\)/)
  assert.match(workspace, /requestId <= lastHandledConnectionFlowRequestId\.value/)
  assert.match(workspace, /!nativeRuntimeStatus\.value\?\.ready \|\| runtimeProvisioning\.value \|\| connectionActionLoading\.value/)
  assert.match(workspace, /handledConnectionFlowRequestIds\.set\(appStore, requestId\)[\s\S]*await chooseConnectionFile\(\)/)
})

test('chat is answer-first and starter prompts populate the composer', () => {
  const history = read('src/components/chat/ChatHistory.vue')
  const composer = read('src/components/chat/ChatInput.vue')
  const userMessage = read('src/components/chat/ChatUserMessage.vue')

  assert.doesNotMatch(history, />Final response</)
  assert.match(history, /Analysis details/)
  assert.match(history, /const SHOW_EPHEMERAL_TRACE = false/)
  assert.match(composer, /watch\(\(\) => appStore\.currentQuestion/)
  assert.match(composer, /aria-label="Send message"/)
  assert.match(composer, /aria-label="Start voice input"/)
  assert.match(composer, /:placeholder="composerPlaceholder"/)
  assert.match(userMessage, /max-w-\[80%\]/)
})

test('the visual system is offline-safe and uses calm, semantic motion', () => {
  const styles = read('src/style.css')
  const sidebar = read('src/components/layout/UnifiedSidebar.vue')
  const nativeShell = read('../main.go')

  assert.doesNotMatch(styles, /fonts\.googleapis\.com/)
  assert.match(styles, /--font-ui:\s*-apple-system/)
  assert.match(styles, /--color-warning-border:/)
  assert.doesNotMatch(styles, /\.chat-composer-surface:focus-within\s*\{[^}]*transform:/s)
  assert.doesNotMatch(sidebar, /\.sidebar-nav-row:hover,[\s\S]*?transform:\s*translate3d/s)
  assert.match(nativeShell, /BackgroundColour:\s*&options\.RGBA\{R:\s*251,\s*G:\s*248,\s*B:\s*242,\s*A:\s*1\}/)
})

test('settings terminology distinguishes model providers from data sources', () => {
  const settings = read('src/components/modals/SettingsModal.vue')
  const setup = read('src/components/modals/tabs/SetupTab.vue')
  const workspace = read('src/components/modals/tabs/WorkspaceTab.vue')
  const onboarding = read('src/components/onboarding/FirstRunModelOnboarding.vue')

  assert.match(settings, />AI providers</)
  assert.match(settings, /max-w-\[1120px\]/)
  assert.match(workspace, /\{ id: 'connections', label: 'Data sources' \}/)
  assert.match(workspace, /Set up managed runtime/)
  assert.match(workspace, /Company-managed setup/)
  assert.match(workspace, /v-show="isNativeWorkspaceMetadata && activeWorkspaceSection === 'connections'"/)
  assert.match(workspace, /v-show="activeWorkspaceSection === 'ai'"/)
  assert.match(workspace, /placeholder="Search sheets"/)
  assert.match(workspace, /Select all/)
  assert.match(workspace, /visiblePendingColumns/)
  assert.match(workspace, /Create a workspace to add context and data sources\./)
  assert.match(setup, /\{\{ setupHeadline \}\}/)
  assert.doesNotMatch(setup, />Ready to ask a question</)
  assert.doesNotMatch(onboarding, /Step 1 of 3/)
  assert.match(onboarding, />Create a workspace</)
})

test('the code workbench gives Run and code provenance clear hierarchy', () => {
  const code = read('src/components/analysis/CodeTab.vue')
  const runs = read('src/components/analysis/OutputTab.vue')
  const figures = read('src/components/analysis/FigureTab.vue')

  assert.match(code, />\s*Generated code\s*</)
  assert.match(code, />\s*My edits\s*</)
  assert.match(code, /data-code-run/)
  assert.match(code, />\s*\{\{ isRunning \? 'Running…' : 'Run' \}\}\s*</)
  assert.match(code, /border-top-color:\s*var\(--color-on-accent\)/)
  assert.match(runs, /<summary[^>]*>\s*View source code\s*<\/summary>/)
  assert.ok(runs.indexOf('data-execution-stdout') < runs.indexOf('data-execution-code'))
  assert.doesNotMatch(figures, /v-if="appStore\.isCodeRunning"/)
})
