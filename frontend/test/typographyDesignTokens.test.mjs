import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const styles = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf8')

test('typography tokens expose one readable semantic type scale', () => {
  assert.match(styles, /--text-caption: 0\.75rem;/)
  assert.match(styles, /--text-ui: 0\.875rem;/)
  assert.match(styles, /--text-title: 1rem;/)
  assert.match(styles, /--text-heading: 1\.125rem;/)

  assert.match(styles, /--font-size-xs: var\(--text-caption\);/)
  assert.match(styles, /--font-size-sm: var\(--text-ui\);/)
  assert.match(styles, /--font-size-base: var\(--text-title\);/)
  assert.match(styles, /--font-size-lg: var\(--text-heading\);/)

  assert.doesNotMatch(styles, /--text-caption: 0\.6875rem;/)
  assert.doesNotMatch(styles, /--text-ui: 0\.8125rem;/)
})

test('typography tokens define semantic weight and line-height roles', () => {
  assert.match(styles, /--font-weight-body: 400;/)
  assert.match(styles, /--font-weight-label: 500;/)
  assert.match(styles, /--font-weight-heading: 600;/)
  assert.match(styles, /--font-weight-strong: 700;/)
  assert.match(styles, /--font-weight-medium: var\(--font-weight-label\);/)
  assert.match(styles, /--font-weight-semibold: var\(--font-weight-heading\);/)
  assert.match(styles, /--font-weight-bold: var\(--font-weight-strong\);/)

  assert.match(styles, /--line-height-caption: 1\.4;/)
  assert.match(styles, /--line-height-ui: 1\.4;/)
  assert.match(styles, /--line-height-body: 1\.55;/)
  assert.match(styles, /--line-height-heading: 1\.25;/)
  assert.match(styles, /--line-height-tight: var\(--line-height-heading\);/)
})

test('text contrast tokens use semantic roles across themes', () => {
  const sharedThemeAliases = styles.match(/:root,\s*\[data-theme\] \{([\s\S]*?)\n\}/)?.[1] ?? ''

  assert.match(sharedThemeAliases, /--color-text-primary: var\(--color-text-main\);/)
  assert.match(
    sharedThemeAliases,
    /--color-text-secondary: color-mix\(in srgb, var\(--color-text-main\) 28%, var\(--color-text-muted\) 72%\);/,
  )
  assert.match(sharedThemeAliases, /--color-text-tertiary: var\(--color-text-muted\);/)
  assert.match(sharedThemeAliases, /--color-text-sub: var\(--color-text-secondary\);/)
})
