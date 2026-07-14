import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const source = readFileSync(resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceAIConfigSection.vue'), 'utf8')

test('workspace AI tab is directly editable without a nested edit mode', () => {
  assert.doesNotMatch(source, /Edit settings/)
  assert.doesNotMatch(source, /isEditing/)
  assert.doesNotMatch(source, /handleDefaultsChange/)
  assert.match(source, /<div class="mt-4 space-y-5 border-t/)
  assert.match(source, /v-model="useDefaults"/)
})

test('workspace AI save action enables only for a changed payload', () => {
  assert.match(source, /const initialPayloadSignature = ref\(''\)/)
  assert.match(source, /const isDirty = computed\(/)
  assert.match(source, /payloadSignature\(buildPayload\(\)\) !== initialPayloadSignature\.value/)
  assert.match(source, /:disabled="isSaving \|\| !isDirty"/)
  assert.match(source, /initialPayloadSignature\.value = payloadSignature\(buildPayload\(\)\)/)
  assert.match(source, /saveWorkspaceAIConfig\(buildPayload\(\), props\.workspaceId\)/)
})

test('switching to application defaults remains unsaved until Save is pressed', () => {
  assert.doesNotMatch(source, /@change="handleDefaultsChange"/)
  assert.doesNotMatch(source, /resetWorkspaceAIConfig/)
  assert.match(source, /llm_provider_override: useDefaults\.value \? null : form\.provider/)
  assert.match(source, /Unsaved changes/)
})
