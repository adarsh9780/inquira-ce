import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('kernel status defaults to connecting and renders a spinner', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes("const kernelStatus = ref('connecting')"), true)
  assert.equal(source.includes('kernelStatusMeta.showSpinner'), true)
  assert.equal(source.includes('animate-spin'), true)
})

test('missing status is presented as connecting when a workspace is active', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes("case 'missing'"), true)
  assert.equal(source.includes("return { label: 'Connecting', textClass: 'text-blue-700', showSpinner: true }"), true)
})

test('restart action sets kernel status to connecting before API response', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes('async function restartKernel()'), true)
  assert.equal(source.includes("kernelStatus.value = 'connecting'"), true)
})
