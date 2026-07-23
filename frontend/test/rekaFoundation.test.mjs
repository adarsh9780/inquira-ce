import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('owned UI primitives use Reka while product components avoid direct primitive imports', () => {
  const packageJson = JSON.parse(read('package.json'))
  const confirmation = read('src/components/modals/ConfirmationModal.vue')
  const alertDialogShell = read('src/components/ui/alert-dialog/AlertDialogShell.vue')
  const dialogShell = read('src/components/ui/dialog/DialogShell.vue')
  const dropdown = read('src/components/ui/HeaderDropdown.vue')

  assert.equal('@headlessui/vue' in packageJson.dependencies, false)
  assert.equal('reka-ui' in packageJson.dependencies, true)
  assert.doesNotMatch(confirmation, /from ['"]reka-ui['"]/)
  assert.match(confirmation, /AlertDialogShell/)
  assert.match(alertDialogShell, /AlertDialogRoot/)
  assert.match(dialogShell, /DialogRoot/)
  assert.match(dropdown, /ComboboxRoot/)
})

test('Reka migrations retain Inquira tokens, reduced motion, and one portal layer policy', () => {
  const dialogShell = read('src/components/ui/dialog/DialogShell.vue')
  const alertDialogShell = read('src/components/ui/alert-dialog/AlertDialogShell.vue')
  const dropdown = read('src/components/ui/HeaderDropdown.vue')

  assert.match(dialogShell, /var\(--color-/)
  assert.match(dialogShell, /prefers-reduced-motion/)
  assert.match(dialogShell, /layer-modal/)
  assert.match(alertDialogShell, /layer-modal/)
  assert.match(dropdown, /dropdownSurfaceClass/)
})
