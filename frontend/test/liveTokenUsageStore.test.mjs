import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store exposes pinia state/actions for live token usage updates', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf8')

  assert.equal(source.includes('const liveTokenUsage = ref(null)'), true)
  assert.equal(source.includes('function setLiveTokenUsage(usage)'), true)
  assert.equal(source.includes('function clearLiveTokenUsage()'), true)
  assert.equal(source.includes('liveTokenUsage,'), true)
  assert.equal(source.includes('setLiveTokenUsage,'), true)
  assert.equal(source.includes('clearLiveTokenUsage,'), true)
})
