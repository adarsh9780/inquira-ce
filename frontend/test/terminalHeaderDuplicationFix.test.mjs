import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('terminal tab hides outer header when tauri PTY terminal is active and consent is granted', () => {
  const terminalTabPath = resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue')
  const source = readFileSync(terminalTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#terminal-toolbar" v-if="isMounted && !(useTauriPty && appStore.terminalConsentGranted)"'), true)
})
