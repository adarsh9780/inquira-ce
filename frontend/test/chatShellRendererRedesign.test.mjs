import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const terminalSource = readFileSync(
    resolve(process.cwd(), 'src/components/chat/TerminalRenderer.vue'),
    'utf-8'
)
const toolCardSource = readFileSync(
    resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'),
    'utf-8'
)

test('TerminalRenderer has Shell badge', () => {
    assert.ok(terminalSource.includes('shell-badge'), 'shell-badge class is present')
    assert.ok(terminalSource.includes('>Shell<'), 'Shell label text is present')
})

test('TerminalRenderer has success and error status indicators', () => {
    assert.ok(terminalSource.includes('shell-status-success'), 'success status class present')
    assert.ok(terminalSource.includes('shell-status-error'), 'error status class present')
    assert.ok(terminalSource.includes('Success'), 'Success label text present')
    assert.ok(terminalSource.includes('Failed'), 'Failed label text present')
})

test('TerminalRenderer has copy output button', () => {
    assert.ok(terminalSource.includes('shell-copy-btn'), 'copy button class present')
    assert.ok(terminalSource.includes('copyOutput'), 'copyOutput function present')
    assert.ok(terminalSource.includes('navigator.clipboard.writeText'), 'clipboard API used')
})

test('TerminalRenderer shows "No output" placeholder', () => {
    assert.ok(terminalSource.includes('shell-no-output'), 'no-output class present')
    assert.ok(terminalSource.includes('No output'), 'No output text present')
})

test('TerminalRenderer uses Prism bash highlighting', () => {
    assert.ok(terminalSource.includes("import Prism from 'prismjs'"), 'Prism import present')
    assert.ok(terminalSource.includes("prismjs/components/prism-bash"), 'Prism bash component imported')
    assert.ok(terminalSource.includes('Prism.highlight'), 'Prism.highlight called')
})

test('TerminalRenderer accepts status prop', () => {
    assert.ok(terminalSource.includes("status:"), 'status prop defined')
    assert.ok(terminalSource.includes("resolvedStatus"), 'resolvedStatus computed present')
})

test('TerminalRenderer uses light card theme (not dark terminal)', () => {
    assert.ok(terminalSource.includes('.shell-card'), 'shell card styles exist')
    assert.ok(terminalSource.includes('background:'), 'shell card sets a background')
    assert.ok(!terminalSource.includes('#0b1220'), 'old dark background removed')
    assert.ok(!terminalSource.includes('#111827'), 'old dark header background removed')
})

test('ToolActivityCard keeps compact text mode without embedded terminal/details', () => {
    assert.ok(!toolCardSource.includes('<TerminalRenderer'), 'terminal component removed from tool activity card')
    assert.ok(!toolCardSource.includes(':status="toolStatus"'), 'no terminal status prop in compact mode')
    assert.ok(!toolCardSource.includes('tool-activity-details'), 'details panel removed')
})

test('ToolActivityCard shows duration label', () => {
    assert.ok(toolCardSource.includes('durationLabel'), 'durationLabel computed present')
    assert.ok(toolCardSource.includes('tool-activity-duration'), 'duration CSS class present')
    assert.ok(toolCardSource.includes('duration_ms'), 'duration_ms accessed from activity')
})

test('ToolActivityCard does not render execution log blocks in compact mode', () => {
    assert.ok(!toolCardSource.includes('Execution logs'), 'execution log heading removed')
    assert.ok(!toolCardSource.includes('tool-activity-log'), 'execution log class removed')
})

test('ToolActivityCard uses Ran/Running verb for bash commands', () => {
    assert.ok(toolCardSource.includes("isComplete ? 'Ran' : 'Running'"), 'verb changes based on status')
})
