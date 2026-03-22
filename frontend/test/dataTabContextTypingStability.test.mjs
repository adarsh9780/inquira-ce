import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('data tab keeps a local schema context draft while the user is typing', () => {
  const dataTabPath = resolve(process.cwd(), 'src/components/modals/DataTab.vue')
  const source = readFileSync(dataTabPath, 'utf-8')

  assert.equal(source.includes('v-model="schemaContextDraft"'), true)
  assert.equal(source.includes('const schemaContextDraft = ref(\'\')'), true)
  assert.equal(source.includes('const isEditingSchemaContext = ref(false)'), true)
  assert.equal(source.includes('if (isEditingSchemaContext.value) return'), true)
  assert.equal(source.includes('const schemaContext = schemaContextDraft.value.trim() || \'\''), true)
  assert.equal(source.includes('await apiService.setContext(schemaContextDraft.value.trim())'), true)
})

test('preference sync preserves the local schema context instead of applying stale echo responses', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('applyPreferencesResponse(response, { preserveLocalSchemaContext: true })'), true)
  assert.equal(source.includes('const preserveLocalSchemaContext = options?.preserveLocalSchemaContext === true'), true)
  assert.equal(source.includes('if (!preserveLocalSchemaContext && typeof prefs?.schema_context === \'string\')'), true)
})
