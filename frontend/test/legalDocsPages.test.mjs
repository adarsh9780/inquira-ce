import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

test('mkdocs nav includes privacy policy and terms of service pages', () => {
  const mkdocsSource = readFileSync(
    resolve(process.cwd(), '../mkdocs.yml'),
    'utf-8',
  )

  assert.equal(mkdocsSource.includes('Privacy Policy: privacy-policy.md'), true)
  assert.equal(mkdocsSource.includes('Terms of Service: terms-of-service.md'), true)
})

test('legal docs pages exist for GitHub Pages links', () => {
  const privacyPath = resolve(process.cwd(), '../docs/privacy-policy.md')
  const termsPath = resolve(process.cwd(), '../docs/terms-of-service.md')

  assert.equal(existsSync(privacyPath), true)
  assert.equal(existsSync(termsPath), true)
  assert.equal(readFileSync(privacyPath, 'utf-8').includes('# Privacy Policy'), true)
  assert.equal(readFileSync(termsPath, 'utf-8').includes('# Terms of Service'), true)
})
