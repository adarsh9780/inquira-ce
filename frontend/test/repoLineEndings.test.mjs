import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('repo pins LF checkouts for text files while preserving native Windows script endings', () => {
  const gitattributesPath = resolve(process.cwd(), '..', '.gitattributes')
  const source = readFileSync(gitattributesPath, 'utf-8')

  assert.equal(source.includes('* text=auto eol=lf'), true)
  assert.equal(source.includes('*.bat text eol=crlf'), true)
  assert.equal(source.includes('*.cmd text eol=crlf'), true)
  assert.equal(source.includes('*.ps1 text eol=crlf'), true)
})
