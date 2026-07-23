import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf8')
const actionsSource = readFileSync(resolve(process.cwd(), 'src/components/startup/StartupFailureActions.vue'), 'utf8')

test('startup failure exposes retry logs and copy-diagnostics actions', () => {
  assert.equal(actionsSource.includes('Restart app'), true)
  assert.equal(actionsSource.includes('Open logs'), true)
  assert.equal(actionsSource.includes('Copy diagnostics'), true)
  assert.equal(actionsSource.includes('aria-label="Startup recovery actions"'), true)
  assert.equal(appSource.includes('@restart="restartDesktopApp"'), true)
})
