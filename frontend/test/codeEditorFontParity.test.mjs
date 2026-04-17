import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code editor uses shared UI font token instead of hardcoded mono stack', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'), 'utf-8')

  assert.equal(source.includes("'.cm-scroller': { fontFamily: 'var(--font-ui)', backgroundColor: '#FFFFFF' }"), true)
  assert.equal(source.includes('Monaco, Menlo, "Ubuntu Mono", monospace'), false)
})
