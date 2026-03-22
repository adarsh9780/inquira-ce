import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

test('docusaurus sidebar includes privacy policy and terms of service pages', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), '../docs-site/sidebars.ts'),
    'utf-8',
  )

  assert.equal(sidebarSource.includes("'privacy-policy'"), true)
  assert.equal(sidebarSource.includes("'terms-of-service'"), true)
})

test('legal docs pages exist for GitHub Pages links', () => {
  const privacyPath = resolve(process.cwd(), '../docs-site/docs/privacy-policy.md')
  const termsPath = resolve(process.cwd(), '../docs-site/docs/terms-of-service.md')

  assert.equal(existsSync(privacyPath), true)
  assert.equal(existsSync(termsPath), true)
  assert.equal(readFileSync(privacyPath, 'utf-8').includes('# Privacy Policy'), true)
  assert.equal(readFileSync(termsPath, 'utf-8').includes('# Terms of Service'), true)
})
