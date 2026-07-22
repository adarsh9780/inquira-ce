import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails startup reads the real Go initialization state', () => {
  const app = read('src/App.vue')
  const goApp = read('../app.go')

  assert.equal(app.includes('wailsApp()?.GetStartupState'), true)
  assert.equal(app.includes('return wailsApp().GetStartupState()'), true)
  assert.equal(goApp.includes('func (a *App) GetStartupState() StartupSnapshot'), true)
})

test('Wails recovery actions use native restart and diagnostics methods', () => {
  const app = read('src/App.vue')
  const goApp = read('../app.go')

  assert.equal(app.includes('wailsApp()?.RestartDesktopApp'), true)
  assert.equal(app.includes('wailsApp()?.OpenStartupLogs'), true)
  assert.equal(goApp.includes('func (a *App) RestartDesktopApp() error'), true)
  assert.equal(goApp.includes('func (a *App) OpenStartupLogs() error'), true)
})

test('external links use the allowlisted Go desktop bridge in Wails', () => {
  const service = read('src/services/externalLinkService.js')
  const goApp = read('../app.go')

  assert.equal(service.includes('app?.OpenExternalURL'), true)
  assert.equal(service.includes('await app.OpenExternalURL(url)'), true)
  assert.equal(goApp.includes('func (a *App) OpenExternalURL(rawURL string) error'), true)
})
