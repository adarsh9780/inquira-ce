import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails startup gates the app on persisted model onboarding', () => {
  const app = read('src/App.vue')
  const service = read('src/services/modelConnectionService.ts')

  assert.match(app, /<FirstRunModelOnboarding/)
  assert.match(app, /modelOnboarding\.checked && modelOnboarding\.required/)
  assert.match(app, /await loadModelOnboardingStatus\(\)/)
  assert.match(app, /handleModelOnboardingComplete/)
  assert.match(app, /uiStore\.openSettings\('workspace-general'\)/)
  assert.match(service, /GetModelOnboardingStatus/)
  assert.match(service, /CompleteModelOnboarding/)
})

test('first-run model onboarding is focused, secure, and cannot be dismissed incomplete', () => {
  const source = read('src/components/onboarding/FirstRunModelOnboarding.vue')

  assert.doesNotMatch(source, /Step 1 of 3/)
  assert.match(source, /First-time setup/)
  assert.match(source, /Connect a model/)
  assert.match(source, /Create a workspace/)
  assert.match(source, /Add local data/)
  assert.match(source, /OpenRouter/)
  assert.match(source, /OpenAI/)
  assert.match(source, /Ollama \(local\)/)
  assert.match(source, /operating system keychain/)
  assert.match(source, /system proxy and certificate settings/)
  assert.match(source, /modelConnectionService\.completeOnboarding\(\)/)
  assert.match(source, /prefers-reduced-motion: reduce/)
  assert.doesNotMatch(source, />Skip</)
  assert.doesNotMatch(source, /Continue without/)
})
