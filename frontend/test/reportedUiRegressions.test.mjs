import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')

test('composer textarea delegates focus treatment to the composer surface', () => {
  const styles = read('src/style.css')

  assert.match(styles, /\.chat-composer-surface textarea:focus-visible\s*\{[^}]*outline:\s*none/s)
  assert.match(styles, /\.chat-composer-surface:focus-within\s*\{[^}]*box-shadow:/s)
})

test('busy analysis uses a stable workspace status dot instead of spinning inside the selector', () => {
  const statusBar = read('src/components/layout/StatusBar.vue')

  assert.match(statusBar, /case 'busy':\s*return \{[^}]*showSpinner:\s*false/s)
  assert.match(statusBar, /case 'starting':[\s\S]*showSpinner:\s*true/)
})
