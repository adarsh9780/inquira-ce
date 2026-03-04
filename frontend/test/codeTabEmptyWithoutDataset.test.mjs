import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code editor template stays empty until user explicitly requests sync/generation', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('const hasSelectedData = computed(() => {'), true)
  assert.equal(source.includes("if (!hasSelectedData.value) {"), true)
  assert.equal(source.includes("toast.info('Select a dataset first')"), true)
  assert.equal(source.includes('await syncTableNameInCode(true)'), false)
  assert.equal(source.includes('watch(() => defaultCodeTemplate.value, (newTemplate) => {'), false)
  assert.equal(source.includes("watch(() => appStore.dataFilePath, (newPath, oldPath) => {"), false)
  assert.equal(source.includes('@click="syncTableNameInCode"'), true)
})
