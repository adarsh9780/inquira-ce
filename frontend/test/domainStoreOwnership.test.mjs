import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('six typed domain stores own state behind the temporary compatibility facade', () => {
  const expectedStores = [
    ['uiStore.ts', "defineStore('ui'"],
    ['preferencesStore.ts', "defineStore('preferences'"],
    ['artifactStore.ts', "defineStore('artifacts'"],
    ['executionStore.ts', "defineStore('execution'"],
    ['workspaceStore.ts', "defineStore('workspaces'"],
    ['conversationStore.ts', "defineStore('conversations'"],
  ]

  for (const [file, marker] of expectedStores) {
    assert.equal(read(`src/stores/${file}`).includes(marker), true, file)
  }

  const facade = read('src/stores/appStore.js')
  assert.match(facade, /storeToRefs\(uiStore\)/)
  assert.match(facade, /storeToRefs\(preferencesStore\)/)
  assert.match(facade, /storeToRefs\(artifactStore\)/)
  assert.match(facade, /storeToRefs\(executionStore\)/)
  assert.match(facade, /storeToRefs\(workspaceStore\)/)
  assert.match(facade, /storeToRefs\(conversationStore\)/)
  assert.match(read('../docs/frontend-state-ownership.md'), /Coordinators/)
})

test('domain stores do not import one another', () => {
  for (const file of [
    'uiStore.ts',
    'preferencesStore.ts',
    'artifactStore.ts',
    'executionStore.ts',
    'workspaceStore.ts',
    'conversationStore.ts',
  ]) {
    assert.doesNotMatch(read(`src/stores/${file}`), /from ['"]\.\/(?:ui|preferences|artifact|execution|workspace|conversation)Store/)
  }
})
