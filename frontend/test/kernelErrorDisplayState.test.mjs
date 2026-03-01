import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('top toolbar shows error state and runtime error text when appStore.runtimeError is present', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes("if (appStore.runtimeError && appStore.activeWorkspaceId)"), true)
  assert.equal(source.includes("return { label: 'Error', textClass: 'text-red-700', showSpinner: false }"), true)
  assert.equal(source.includes('v-if="appStore.runtimeError"'), true)
})

test('missing kernel status does not show connecting spinner when workspace exists', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes("return { label: 'Missing', textClass: 'text-amber-700', showSpinner: false }"), true)
})
