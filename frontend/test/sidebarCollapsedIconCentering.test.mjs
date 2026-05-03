import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// Regression test: when the sidebar is collapsed (w-[64px]) every row must
// render ONLY the icon container and center it within the 64px column.
//
// The previous implementation kept the label <div> in the DOM with
// `max-w-0 opacity-0`. Because the label <div> still participates in flex
// layout, browsers would reserve a sub-pixel of space for its hidden text
// content, which visibly shifted every icon a few pixels to the right of
// center. The fix is to omit the label entirely via `v-if` when collapsed,
// so each row contains a single `h-6 w-6` icon that `justify-center`
// can center perfectly.

test('UnifiedSidebar rows omit label <div> when collapsed so icons center cleanly', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  // The label containers must be guarded by `v-if="!appStore.isSidebarCollapsed"`
  // rather than toggling `max-w-0 opacity-0` at runtime. If the invisible
  // label survives in the DOM it will push the icon off-center on the
  // collapsed rail.
  assert.equal(
    source.includes("max-w-0 opacity-0 ml-0"),
    false,
    'Collapsed rows must not keep label <div>s in the DOM with max-w-0; render them with v-if instead.'
  )

  // Every label container should be gated by v-if on the collapsed flag.
  const labelGuardCount = (source.match(/v-if="!appStore\.isSidebarCollapsed"/g) || []).length
  assert.ok(
    labelGuardCount >= 5,
    `Expected at least 5 label <div>s gated by v-if="!appStore.isSidebarCollapsed"; found ${labelGuardCount}.`
  )
})

test('UnifiedSidebar collapsed rows rely on justify-center + fixed 24px icon for centering', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  // Collapsed sidebar width is exactly 64px; icons are 24px (h-6 w-6).
  assert.equal(source.includes("'w-[64px]'"), true, 'Collapsed sidebar must be 64px wide.')

  // The outer brand row must explicitly add `justify-center` at the container
  // level when collapsed so the brand button (which no longer stretches to
  // w-full) sits dead-center inside the 64px column.
  assert.equal(
    source.includes("'px-0 justify-center'"),
    true,
    'Brand row must apply justify-center to its container when collapsed.'
  )

  // All interactive rows below the brand must use justify-center when collapsed.
  const justifyCenterCount = (source.match(/justify-center py-2/g) || []).length
  assert.ok(
    justifyCenterCount >= 4,
    `Expected at least 4 rows using "justify-center py-2" when collapsed; found ${justifyCenterCount}.`
  )

  // Every icon container keeps a stable 24px square (`h-6 w-6`) with `shrink-0`
  // so flex math stays predictable inside the 64px rail.
  assert.ok(
    source.includes('h-6 w-6 shrink-0 items-center justify-center'),
    'Icon containers must stay h-6 w-6 with shrink-0 and inner centering.'
  )

  // The parent navigation wrapper drops horizontal padding when collapsed so
  // icons are centered against the 64px edge, not against an inset column.
  assert.ok(
    source.includes("'px-0 scrollbar-hidden'"),
    'Navigation wrapper must drop horizontal padding when collapsed.'
  )
})

test('UnifiedSidebar conversation rows drop trailing ellipsis button when collapsed', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  // The ellipsis menu used to stay in the DOM with `hidden` on the class
  // binding, which left a stray `pl-2` on a display:none sibling. We now
  // gate the whole wrapper with v-if to eliminate any ghost padding.
  assert.equal(
    source.includes("appStore.isSidebarCollapsed ? 'hidden' :"),
    false,
    'Ellipsis wrapper must not be toggled via display:none; remove it via v-if instead.'
  )

  assert.ok(
    source.includes('v-if="!appStore.isSidebarCollapsed" class="relative shrink-0 transition-opacity pl-2'),
    'Ellipsis wrapper should be rendered only when the sidebar is expanded.'
  )
})
