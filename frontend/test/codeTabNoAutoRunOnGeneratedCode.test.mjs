import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('CodeTab generatedCode watcher does not auto-execute runCode', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'components', 'analysis', 'CodeTab.vue')
  const source = fs.readFileSync(filePath, 'utf8')

  const watcherStart = source.indexOf('watch(() => appStore.generatedCode, (newCode) => {')
  assert.notEqual(watcherStart, -1)
  const watcherEnd = source.indexOf('watch(() => appStore.isLoading, (loading) => {', watcherStart)
  assert.notEqual(watcherEnd, -1)

  const watcherBody = source.slice(watcherStart, watcherEnd)
  assert.equal(watcherBody.includes('runCode()'), false)
})
