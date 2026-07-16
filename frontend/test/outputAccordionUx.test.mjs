import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('runs render one quiet vertical notebook block with full-width output controls', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-right"'), true)
  assert.equal(source.includes('v-for="execution in visibleExecutionItems"'), true)
  assert.equal(source.includes('data-runs-feed'), true)
  assert.equal(source.includes('data-user-run'), true)
  assert.equal(source.includes('data-run-body'), true)
  assert.equal(source.includes('data-execution-code'), true)
  assert.equal(source.includes('data-execution-stdout'), true)
  assert.equal(source.includes('data-execution-stderr'), true)
  assert.equal(source.includes('buildUserRunItems'), true)
  assert.equal(source.includes('<RunTableOutput'), true)
  assert.equal(source.includes('<RunChartOutput'), true)
  assert.equal(source.includes('Open in Tables'), true)
  assert.equal(source.includes('Open in Charts'), true)
  assert.equal(source.includes('aria-label="Delete run"'), true)
  assert.equal(source.includes('appStore.removeTerminalEntry(execution.entryId)'), true)
  assert.equal(source.includes('Open full output'), true)
  assert.equal(source.includes('focusedRunId'), true)
  assert.equal(source.includes('text-[11px] font-mono leading-4'), true)
  assert.equal(source.includes('class="mt-3 min-w-0 border-t pt-4"'), true)
  assert.equal(source.includes('divide-y'), true)
  assert.equal(source.includes('rounded-xl'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('md:grid-cols-[minmax(15rem,0.85fr)_minmax(0,1.15fr)]'), false)
  assert.equal(source.includes('>Code<'), false)
  assert.equal(source.includes('>Output<'), false)
  assert.equal(source.includes('buildUnifiedResultItems'), false)
})
