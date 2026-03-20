import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('DataTab points users to Models tab for API key setup', () => {
  const path = resolve(process.cwd(), 'src/components/modals/DataTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Models tab first'), true)
  assert.equal(source.includes('Please set your API key in the Models tab first.'), true)
})
