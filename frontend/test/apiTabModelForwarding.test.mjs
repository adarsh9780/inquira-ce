import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('ApiTab forwards selected model when testing provider API key', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('apiService.testGeminiApi(key, appStore.selectedModel, appStore.llmProvider)'), true)
})

test('ApiTab saves dedicated coding model preference', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Coding Model (subagent)'), true)
  assert.equal(source.includes('selected_coding_model: appStore.selectedCodingModel'), true)
  assert.equal(source.includes('handleCodingModelChange'), true)
})

test('ApiTab routes runner package installs to terminal guidance instead of inline installer form', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Runner Packages'), false)
  assert.equal(source.includes('Use the Terminal tab for package installs'), true)
  assert.equal(source.includes('openTerminalForPackageInstall'), true)
  assert.equal(source.includes('appStore.toggleTerminal()'), true)
})
