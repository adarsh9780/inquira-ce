import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails startup reads the real Go initialization state', () => {
  const app = read('src/App.vue')
  const goApp = read('../app.go')

  assert.equal(app.includes('const app = wailsApp()'), true)
  assert.equal(app.includes('if (app?.GetStartupState)'), true)
  assert.equal(app.includes('return app.GetStartupState()'), true)
  assert.equal(goApp.includes('func (a *App) GetStartupState() StartupSnapshot'), true)
})

test('Wails recovery actions use native restart and diagnostics methods', () => {
  const app = read('src/App.vue')
  const goApp = read('../app.go')

  assert.equal(app.includes('app?.RestartDesktopApp'), true)
  assert.equal(app.includes('app?.OpenStartupLogs'), true)
  assert.equal(goApp.includes('func (a *App) RestartDesktopApp() error'), true)
  assert.equal(goApp.includes('func (a *App) OpenStartupLogs() error'), true)
})

test('external links use the allowlisted Go desktop bridge in Wails', () => {
  const service = read('src/services/externalLinkService.ts')
  const goApp = read('../app.go')

  assert.equal(service.includes('app?.OpenExternalURL'), true)
  assert.equal(service.includes('await app.OpenExternalURL(url)'), true)
  assert.equal(goApp.includes('func (a *App) OpenExternalURL(rawURL string) error'), true)
})
