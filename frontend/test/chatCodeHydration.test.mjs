import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat response hydrates editor content directly from code/current_code payload', () => {
  const chatPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatPath, 'utf-8')

  assert.equal(source.includes('const finalCode = (code ?? current_code ?? \'\').toString()'), true)
  assert.equal(source.includes('appStore.setGeneratedCode(finalCode)'), true)
  assert.equal(source.includes('appStore.setPythonFileContent(finalCode)'), true)
})

test('v1 analyze helper returns payload directly without double-unwrapping .data', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('return v1Api.chat.analyze(payload)'), true)
  assert.equal(source.includes('v1Api.chat.analyze(payload).then((res) => res.data)'), false)
})
