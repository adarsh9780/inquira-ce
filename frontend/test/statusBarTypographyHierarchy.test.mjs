import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf8')

test('status bar uses one compact metadata size with regular default weight', () => {
  assert.match(source, /class="status-bar h-7[^\"]*text-\[11px\] font-normal/)
  assert.doesNotMatch(source, /class="status-bar h-7[^\"]*font-medium/)
  assert.match(source, /truncate font-medium text-\[var\(--color-text-main\)\]/)
  assert.match(source, /hidden font-medium sm:inline/)
  assert.doesNotMatch(source, /hidden text-\[11px\] font-semibold sm:inline/)
})

test('changing status-bar numbers use tabular numerals for stable alignment', () => {
  assert.match(source, /gap-1 h-full px-1 tabular-nums/)
  assert.match(source, /items-center tabular-nums text-\[var\(--color-text-muted\)\] tracking-tight/)
  assert.equal((source.match(/font-medium tabular-nums/g) || []).length >= 3, true)
})
