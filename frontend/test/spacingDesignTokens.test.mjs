import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const styles = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf8')

test('spacing primitives use a rem-based quarter-step scale', () => {
  const expectedScale = new Map([
    ['--space-0', '0rem'],
    ['--space-1', '0.25rem'],
    ['--space-2', '0.5rem'],
    ['--space-3', '0.75rem'],
    ['--space-4', '1rem'],
    ['--space-5', '1.25rem'],
    ['--space-6', '1.5rem'],
    ['--space-8', '2rem'],
    ['--space-12', '3rem'],
  ])

  for (const [token, value] of expectedScale) {
    assert.match(styles, new RegExp(`${token}: ${value.replace('.', '\\.')};`))
  }
})

test('semantic spacing tokens encode related, container, and section relationships', () => {
  const expectedAliases = new Map([
    ['--space-related-tight', '--space-1'],
    ['--space-related', '--space-2'],
    ['--space-control-inline', '--space-3'],
    ['--space-container', '--space-4'],
    ['--space-container-roomy', '--space-6'],
    ['--space-section', '--space-8'],
  ])

  for (const [token, primitive] of expectedAliases) {
    assert.equal(styles.includes(`${token}: var(${primitive});`), true)
  }
})

test('existing component spacing aliases consume the shared scale', () => {
  const componentAliases = [
    '--space-overlay-gap',
    '--space-sidebar-brand-gap',
    '--space-sidebar-panel-inline',
    '--space-sidebar-list-indent',
    '--space-sidebar-row-inline-end',
    '--space-sidebar-section-block-start',
    '--space-sidebar-section-block-end',
    '--space-sidebar-row-gap',
  ]

  for (const token of componentAliases) {
    assert.match(styles, new RegExp(`${token}: var\\(--space-[^)]+\\);`))
  }
})
