import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code editor template stays empty until a dataset is selected', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('const hasSelectedData = computed(() => {'), true)
  assert.equal(source.includes("if (!hasSelectedData.value) {"), true)
  assert.equal(source.includes("toast.info('Select a dataset first')"), true)
  assert.equal(source.includes('if (hasSelectedData.value) {'), true)
  assert.equal(source.includes('watch(() => defaultCodeTemplate.value, (newTemplate) => {'), true)
  assert.equal(source.includes('if (!hasSelectedData.value) return'), true)
  assert.equal(source.includes("const hasSelectedPath = String(newPath || '').trim() !== ''"), true)
})
