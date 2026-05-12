import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('UI preferences service only exposes generic preference persistence helpers', () => {
  const servicePath = resolve(process.cwd(), 'src/services/uiPreferencesService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('async getPreferences()'), true)
  assert.equal(source.includes('async savePreferences(prefs)'), true)
  assert.equal(source.includes('hasSeenWalkthrough'), false)
  assert.equal(source.includes('markWalkthroughAsSeen'), false)
})
