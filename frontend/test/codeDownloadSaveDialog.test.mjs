import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code download uses save dialog flow instead of silent anchor download', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("import { persistExportFile } from '../../utils/exportFile'"), true)
  assert.equal(source.includes('const exported = await persistExportFile({'), true)
  assert.equal(source.includes("toast.info('Export canceled')"), true)
  assert.equal(source.includes("toast.success('Export complete'"), true)
  assert.equal(source.includes('link.download ='), false)
  assert.equal(source.includes("document.createElement('a')"), false)
})
