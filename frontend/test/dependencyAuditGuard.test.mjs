import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('frontend dependencies avoid vulnerable markdown-it-katex package', () => {
  const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf-8'))
  const dependencies = packageJson.dependencies || {}

  assert.equal(Object.hasOwn(dependencies, 'markdown-it-katex'), false)
  assert.equal(Object.hasOwn(dependencies, '@vscode/markdown-it-katex'), true)
})
