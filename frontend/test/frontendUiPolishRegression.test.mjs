import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')

test('settings modal is viewport bounded and exposes dialog keyboard semantics', () => {
  const source = read('src/components/modals/SettingsModal.vue')

  assert.match(source, /h-\[min\(47\.5rem,calc\(100dvh-2rem\)\)\]/)
  assert.match(source, /max-w-\[70rem\]/)
  assert.match(source, /<DialogShell/)
  assert.match(source, /:description="activeSectionDescription"/)
  assert.match(source, /headerless/)
  assert.match(source, /@close="closeModal"/)
})

test('centered dialog animations do not compose competing transform translations', () => {
  const dialog = read('src/components/ui/dialog/DialogShell.vue')
  const alertDialog = read('src/components/ui/alert-dialog/AlertDialogShell.vue')

  assert.match(dialog, /translate: -50% calc\(-50% \+ 0\.5rem\)/)
  assert.doesNotMatch(dialog, /transform: translate\(-50%/)
  assert.match(alertDialog, /translate: -50% calc\(-50% \+ 0\.5rem\)/)
  assert.doesNotMatch(alertDialog, /transform: translate\(-50%/)
})

test('inactive settings panels are removed from keyboard and accessibility navigation', () => {
  const source = read('src/components/modals/SettingsModal.vue')

  assert.equal((source.match(/v-if="currentPanel ===/g) || []).length, 5)
  assert.doesNotMatch(source, /handleDialogKeydown/)
})

test('model selector uses a bounded scroll surface and full-name tooltips', () => {
  const selector = read('src/components/ui/ModelSelector.vue')
  const dropdown = read('src/components/ui/HeaderDropdown.vue')

  assert.match(selector, /:dropdown-min-width="288"/)
  assert.match(dropdown, /max-h-\[240px\] overflow-y-auto/)
  assert.match(dropdown, /:title="option\.label"/)
  assert.match(selector, /:trigger-label="selectedLabel"/)
})

test('floating action menu supports menu roles, arrow navigation, and focus restoration', () => {
  const source = read('src/components/ui/FloatingActionMenu.vue')

  assert.match(source, /role="menu"/)
  assert.match(source, /role="menuitem"/)
  assert.match(source, /\['ArrowDown', 'ArrowUp', 'Home', 'End'\]/)
  assert.match(source, /enabledItems\(\)\[0\]\?\.focus/)
  assert.match(source, /triggerElement\?\.focus/)
})

test('workspace panes have compact navigation and accessible pointer resizers', () => {
  const source = read('src/components/layout/RightPanel.vue')

  assert.match(source, /isCompactLayout/)
  assert.match(source, /compactPane === 'work'/)
  assert.match(source, /compactPane === 'data'/)
  assert.match(source, /< 760/)
  assert.equal((source.match(/role="separator"/g) || []).length, 2)
  assert.match(source, /@pointerdown="startResizeX"/)
  assert.match(source, /handleResizeXKeydown/)
  assert.match(source, /handleResizeYKeydown/)
})

test('composer defers readiness guidance and keeps its direct controls labelled', () => {
  const source = read('src/components/chat/ChatInput.vue')

  assert.doesNotMatch(source, /Enter your OpenRouter API key/)
  assert.doesNotMatch(source, /missingSetupRequirements/)
  assert.doesNotMatch(source, /<InlineNotice/)
  assert.doesNotMatch(source, /<ModelSelector/)
  assert.match(source, /aria-label="Attach images"/)
  assert.match(source, /aria-label="Start voice input"/)
  assert.match(source, /aria-label="Send message"/)
  assert.match(source, /aria-label="Stop generation"/)
})

test('global UI honors reduced motion and startup states are announced', () => {
  const styles = read('src/style.css')
  const startup = read('src/components/startup/StartupScreen.vue')
  const failure = read('src/components/startup/StartupFailureScreen.vue')
  const overlay = read('src/components/startup/BlockingOperationOverlay.vue')

  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/)
  assert.match(styles, /transition-duration: 0\.01ms !important/)
  assert.match(startup, /role="status"/)
  assert.match(failure, /role="alert"/)
  assert.match(overlay, /:aria-hidden="active \? 'false' : 'true'"/)
})
