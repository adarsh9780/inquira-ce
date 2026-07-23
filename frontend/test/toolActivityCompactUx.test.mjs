import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const toolCardSource = readFileSync(
  resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'),
  'utf-8',
)

test('tool activity keeps compact text mode without embedded terminal details', () => {
  assert.equal(toolCardSource.includes('<TerminalRenderer'), false)
  assert.equal(toolCardSource.includes(':status="toolStatus"'), false)
  assert.equal(toolCardSource.includes('tool-activity-details'), false)
})

test('tool activity shows duration without execution-log blocks', () => {
  assert.equal(toolCardSource.includes('durationLabel'), true)
  assert.equal(toolCardSource.includes('tool-activity-duration'), true)
  assert.equal(toolCardSource.includes('duration_ms'), true)
  assert.equal(toolCardSource.includes('Execution logs'), false)
  assert.equal(toolCardSource.includes('tool-activity-log'), false)
})

test('tool activity uses Ran and Running verbs for shell commands', () => {
  assert.equal(toolCardSource.includes("isComplete ? 'Ran' : 'Running'"), true)
})
