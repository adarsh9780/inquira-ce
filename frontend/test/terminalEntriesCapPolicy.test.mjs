import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store caps and trims terminal entries to bound memory usage', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('const MAX_TERMINAL_ENTRIES = 400'), true)
  assert.equal(source.includes('const MAX_TERMINAL_STREAM_CHARS = 200000'), true)
  assert.equal(source.includes('const MAX_TERMINAL_TOTAL_CHARS = 2000000'), true)
  assert.equal(source.includes('const terminalEntriesTrimmedCount = ref(0)'), true)
  assert.equal(source.includes('function trimTerminalStream(text, maxChars = MAX_TERMINAL_STREAM_CHARS)'), true)
  assert.equal(source.includes('function enforceTerminalEntryLimits() {'), true)
  assert.equal(source.includes('while (terminalEntries.value.length > MAX_TERMINAL_ENTRIES)'), true)
  assert.equal(source.includes('while (totalChars > MAX_TERMINAL_TOTAL_CHARS && terminalEntries.value.length > 1)'), true)
  assert.equal(source.includes('terminalEntriesTrimmedCount.value += trimmed'), true)
  assert.equal(source.includes('enforceTerminalEntryLimits()'), true)
})
