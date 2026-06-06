import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf8')
const actionsSource = readFileSync(resolve(process.cwd(), 'src/components/startup/StartupFailureActions.vue'), 'utf8')
const tauriSource = readFileSync(resolve(process.cwd(), '../src-tauri/src/lib.rs'), 'utf8')

test('startup failure exposes retry logs and copy-diagnostics actions', () => {
  assert.equal(actionsSource.includes('Restart app'), true)
  assert.equal(actionsSource.includes('Open logs'), true)
  assert.equal(actionsSource.includes('Copy diagnostics'), true)
  assert.equal(actionsSource.includes('aria-label="Startup recovery actions"'), true)
  assert.equal(appSource.includes('@restart="restartDesktopApp"'), true)
})

test('desktop startup state read failures do not masquerade as ready', () => {
  const catchStart = appSource.indexOf("console.warn('⚠️ Failed to read desktop startup state from Tauri:'")
  const catchEnd = appSource.indexOf('async function subscribeDesktopStartupEvents', catchStart)
  const catchBlock = appSource.slice(catchStart, catchEnd)
  assert.equal(appSource.includes("error: 'Could not read desktop service startup state."), true)
  assert.equal(catchBlock.includes("return { ready: true, error: '', message: '' }"), false)
})

test('tauri registers startup log and restart recovery commands', () => {
  assert.equal(tauriSource.includes('fn open_startup_logs('), true)
  assert.equal(tauriSource.includes('fn restart_desktop_app('), true)
  assert.equal(tauriSource.includes('open_startup_logs,'), true)
  assert.equal(tauriSource.includes('restart_desktop_app,'), true)
})
