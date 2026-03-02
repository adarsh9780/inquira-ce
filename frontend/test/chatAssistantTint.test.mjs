import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('assistant chat bubble uses yellow-tinted surface while user bubble styling remains unchanged', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'components', 'chat', 'ChatHistory.vue')
  const source = fs.readFileSync(filePath, 'utf8')

  assert.equal(source.includes('style="background-color: #EDE9DE;"'), true)
  assert.equal(source.includes('background-color: color-mix(in srgb, var(--color-base) 55%, #FDE68A 45%);'), true)
  assert.equal(source.includes('bg-white px-4 py-3'), false)
})
