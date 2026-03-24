import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('desktop startup hides the main window until native startup finishes', () => {
  const tauriConfig = readFileSync(
    resolve(process.cwd(), '../src-tauri/tauri.conf.json'),
    'utf-8',
  )
  const source = readFileSync(
    resolve(process.cwd(), '../src-tauri/src/lib.rs'),
    'utf-8',
  )

  assert.equal(tauriConfig.includes('"visible": false'), true)
  assert.equal(source.includes('fn show_main_window(app: &tauri::AppHandle)'), true)
  assert.equal(source.includes('show_main_window(&app.handle());'), true)
})

test('desktop startup exposes one native startup-state handoff to the frontend', () => {
  const source = readFileSync(
    resolve(process.cwd(), '../src-tauri/src/lib.rs'),
    'utf-8',
  )

  assert.equal(source.includes('struct StartupSnapshot'), true)
  assert.equal(source.includes('struct StartupState(Mutex<StartupSnapshot>);'), true)
  assert.equal(source.includes('fn get_startup_state(app: tauri::AppHandle) -> StartupSnapshot'), true)
  assert.equal(source.includes('update_startup_state(&app.handle(), true, "")'), true)
})
