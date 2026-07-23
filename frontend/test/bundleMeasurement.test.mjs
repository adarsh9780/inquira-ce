import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

test('frontend exposes repeatable machine-readable bundle measurement commands', () => {
  const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'))
  const viteConfig = readFileSync(resolve(process.cwd(), 'vite.config.js'), 'utf8')
  const reporter = readFileSync(resolve(process.cwd(), 'scripts/bundle-report.mjs'), 'utf8')

  assert.match(packageJson.scripts['bundle:baseline'], /bundle:report/)
  assert.match(packageJson.scripts['bundle:check'], /check-bundle-budget/)
  assert.match(viteConfig, /manifest:\s*true/)
  for (const feature of ['settings', 'code', 'terminal', 'table', 'figure', 'other']) {
    assert.match(reporter, new RegExp(`${feature}:`))
  }
  assert.match(reporter, /duplicatePackages/)
  assert.match(reporter, /sharedChunks/)
})
