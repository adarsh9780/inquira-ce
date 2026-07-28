import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const styles = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf8')

test('depth tokens expose a semantic tonal surface hierarchy', () => {
  assert.match(styles, /--color-surface-page: var\(--color-shell-backdrop\);/)
  assert.match(styles, /--color-surface-container: var\(--color-surface\);/)
  assert.match(styles, /--color-surface-raised: var\(--color-base\);/)
  assert.match(styles, /--color-surface-overlay: var\(--color-panel-elevated\);/)
})

test('light and dark themes provide appropriate depth lighting', () => {
  const warmTheme = styles.match(/:root,\s*:root\[data-theme="warm"\],[\s\S]*?\{([\s\S]*?)\n\}/)?.[1] ?? ''
  const midnightTheme = styles.match(/:root\[data-theme="midnight"\],[\s\S]*?\{([\s\S]*?)\n\}/)?.[1] ?? ''

  assert.match(warmTheme, /--color-depth-highlight: rgb\(255 255 255 \/ 72%\);/)
  assert.match(warmTheme, /--color-depth-shadow-strong: rgb\(30 36 48 \/ 24%\);/)
  assert.match(midnightTheme, /--color-depth-highlight: rgb\(255 255 255 \/ 7%\);/)
  assert.match(midnightTheme, /--color-depth-shadow-strong: rgb\(0 0 0 \/ 50%\);/)
})

test('elevation tiers combine a light-facing edge with cast shadows', () => {
  assert.match(
    styles,
    /--shadow-elevation-sm: inset 0 1px 0 var\(--color-depth-highlight\), 0 1px 2px var\(--color-depth-shadow-soft\);/,
  )
  assert.match(
    styles,
    /--shadow-elevation-md: inset 0 1px 0 var\(--color-depth-highlight\), 0 2px 4px var\(--color-depth-shadow-soft\), 0 8px 18px var\(--color-depth-shadow-medium\);/,
  )
  assert.match(
    styles,
    /--shadow-elevation-lg: inset 0 1px 0 var\(--color-depth-highlight\), 0 6px 16px var\(--color-depth-shadow-medium\), 0 24px 48px var\(--color-depth-shadow-strong\);/,
  )
  assert.match(
    styles,
    /--shadow-recessed: inset 0 2px 4px var\(--color-depth-shadow-soft\), inset 0 -1px 0 var\(--color-depth-highlight\);/,
  )

  assert.match(styles, /--shadow-button: var\(--shadow-elevation-sm\);/)
  assert.match(styles, /--shadow-lifted: var\(--shadow-elevation-md\);/)
  assert.match(styles, /--shadow-modal: var\(--shadow-elevation-lg\);/)
})

test('shared option groups and inputs consume the depth tiers', () => {
  assert.match(styles, /\.segmented-control \{[\s\S]*box-shadow: var\(--shadow-recessed\);/)
  assert.match(styles, /\.segmented-control-item-active \{[\s\S]*box-shadow: var\(--shadow-elevation-sm\);/)
  assert.match(styles, /\.input-base \{[\s\S]*box-shadow: var\(--shadow-recessed\);/)
  assert.match(
    styles,
    /\.input-base:focus \{[\s\S]*box-shadow: var\(--shadow-recessed\), 0 0 0 3px/,
  )
})
