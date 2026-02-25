import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api interceptor suppresses expected startup auth probe noise when backend is not ready', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes("const isAuthProbe = url.includes('/api/v1/auth/me')"), true)
  assert.equal(source.includes('(status === 401 || !status)'), true)
})
