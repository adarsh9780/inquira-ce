import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store exposes schema file id and upload state actions used by dataset/settings flows', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appCoordinatorStore.js')
  const source = `${readFileSync(resolve(process.cwd(), 'src/stores/workspaceStore.ts'), 'utf-8')}\n${readFileSync(appStorePath, 'utf-8')}`

  assert.equal(source.includes("const schemaFileId = ref('')"), true)
  assert.equal(source.includes('const isSchemaFileUploaded = ref(false)'), true)
  assert.equal(source.includes('function setSchemaFileId(schemaId) {'), true)
  assert.equal(source.includes('function setIsSchemaFileUploaded(uploaded) {'), true)
  assert.equal(source.includes('setSchemaFileId,'), true)
  assert.equal(source.includes('setIsSchemaFileUploaded,'), true)
})
