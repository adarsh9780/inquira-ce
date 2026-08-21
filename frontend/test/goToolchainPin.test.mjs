import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const repositoryRoot = resolve(import.meta.dirname, '..', '..')
const read = (path) => readFileSync(resolve(repositoryRoot, path), 'utf8')

test('build, CI, and release use the audited Go toolchain patch', () => {
  const expectedVersion = '1.26.6'

  assert.match(read('go.mod'), new RegExp(`toolchain go${expectedVersion.replaceAll('.', '\\.')}`))
  assert.match(read('Makefile'), new RegExp(`GO_VERSION := ${expectedVersion.replaceAll('.', '\\.')}`))
  assert.equal(read('.github/workflows/ci.yml').match(/go-version: "1\.26\.6"/g)?.length, 2)
  assert.match(read('.github/workflows/release.yml'), /GO_VERSION: "1\.26\.6"/)
})
