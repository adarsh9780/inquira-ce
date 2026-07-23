import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('provider credentials cross the Wails bridge and persist in the OS keychain', () => {
  const service = readFileSync(
    resolve(process.cwd(), 'src/services/modelConnectionService.js'),
    'utf-8',
  )
  const goApp = readFileSync(resolve(process.cwd(), '../app.go'), 'utf-8')
  const secrets = readFileSync(
    resolve(process.cwd(), '../internal/modelconfig/secrets.go'),
    'utf-8',
  )

  assert.equal(service.includes("callWails('VerifyProviderAPIKey'"), true)
  assert.equal(service.includes("callWails('SaveProviderConfiguration'"), true)
  assert.equal(service.includes("callWails('DeleteProviderAPIKey'"), true)
  assert.equal(goApp.includes('func (a *App) VerifyProviderAPIKey(provider, apiKey string)'), true)
  assert.equal(goApp.includes('func (a *App) SaveProviderConfiguration(request modelconfig.SaveRequest)'), true)
  assert.equal(goApp.includes('func (a *App) DeleteProviderAPIKey(provider string)'), true)
  assert.equal(secrets.includes('keyring.Set('), true)
  assert.equal(secrets.includes('keyring.Get('), true)
  assert.equal(secrets.includes('keyring.Delete('), true)
})
