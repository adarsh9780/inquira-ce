import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab does not auto-populate code template when dataset changes', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('await syncTableNameInCode(true)'), false)
  assert.equal(source.includes('watch(() => defaultCodeTemplate.value'), false)
  assert.equal(source.includes('watch(() => appStore.dataFilePath, (newPath, oldPath) => {'), false)
  assert.equal(source.includes('const defaultCodeTemplate = computed(() => {'), true)
  assert.equal(source.includes('@click="syncTableNameInCode"'), true)
})
