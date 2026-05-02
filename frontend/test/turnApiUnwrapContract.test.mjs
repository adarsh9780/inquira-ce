import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('turn api helpers return interceptor-unwrapped axios payloads directly', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/services/apiService.js'), 'utf-8')

  assert.equal(source.includes("axios.get(`/api/v1/conversations/${conversationId}/final-turn`).then((response) => response.data)"), false)
  assert.equal(source.includes("axios.post(`/api/v1/conversations/${conversationId}/final-turn/rerun`).then((response) => response.data)"), false)
  assert.equal(source.includes("return axios.get(`/api/v1/conversations/${conversationId}/final-turn`)"), true)
  assert.equal(source.includes("return axios.post(`/api/v1/conversations/${conversationId}/final-turn/rerun`)"), true)
})
