import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('apiService testGeminiApi uses generated client and 404 fallback to v1 admin route', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('testGeminiApiKeyApiV1AdminTestGeminiPost'), true)
  assert.equal(source.includes('testGeminiApiKeyApiTestGeminiPost'), true)
  assert.equal(source.includes("error?.response?.status === 404"), true)
  assert.equal(source.includes("axios.post('/api/v1/admin/test-gemini'"), true)
})

test('orval generation uses exported local openapi spec', () => {
  const configPath = resolve(process.cwd(), 'orval.config.js')
  const packagePath = resolve(process.cwd(), 'package.json')
  const config = readFileSync(configPath, 'utf-8')
  const pkg = readFileSync(packagePath, 'utf-8')

  assert.equal(config.includes("target: './openapi.json'"), true)
  assert.equal(pkg.includes('"export-openapi"'), true)
  assert.equal(pkg.includes('backend/scripts/export_openapi.py ./openapi.json'), true)
})
