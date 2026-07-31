import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('packaged message rendering registers Prism languages without unsafe side-effect modules', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/utils/messageRendering.ts'), 'utf-8')

  assert.equal(source.includes("from 'prismjs/components/"), false)
  assert.equal(source.includes('registerPrismLanguages(Prism)'), true)
  assert.equal(source.includes("typeof markdownItKatexModule === 'function'"), true)
  assert.equal(source.includes("if (typeof markdownItKatex === 'function')"), true)
})
