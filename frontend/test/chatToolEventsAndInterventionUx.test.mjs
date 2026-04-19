import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input handles tool and intervention SSE events', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(source.includes("evt.event === 'tool_call'"), true)
  assert.equal(source.includes("evt.event === 'tool_progress'"), true)
  assert.equal(source.includes("evt.event === 'tool_result'"), true)
  assert.equal(source.includes("evt.event === 'intervention_request'"), true)
  assert.equal(source.includes("evt.event === 'intervention_response'"), true)
  assert.equal(source.includes("evt.event === 'agent_status'"), true)
  assert.equal(source.includes("output: evt.data?.detail || evt.data?.output || ''"), true)
  assert.equal(source.includes("output: String(payload.plan || '')"), true)
  assert.equal(source.includes('payload.answer'), false)
  assert.equal(source.includes('payload.code'), false)
  assert.equal(source.includes('payload.current_code'), false)
})

test('chat history renders tool cards and intervention component', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('<ToolActivityCard'), true)
  assert.equal(source.includes('<AgentIntervention'), true)
  assert.equal(source.includes('submitInterventionResponse(message, payload)'), true)
  assert.equal(source.includes('v1RespondChatIntervention'), true)
  assert.equal(source.includes('&gt; {{ row.summary }}'), false)
})

test('tool activity summary avoids duplicate textual chevron prefix', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')
  assert.equal(source.includes('&gt; {{ summaryText }}'), false)
})

test('tool activity card prefers streamed explanation text when present', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')
  assert.equal(source.includes('props.activity?.explanation'), true)
  assert.equal(source.includes('delete args.explanation'), true)
})

test('app store preserves tool-call explanations in stream trace', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')
  assert.equal(source.includes('existing.explanation = String(event.explanation || existing.explanation || \'\')'), true)
  assert.equal(source.includes('explanation: String(event.explanation || \'\')'), true)
})

test('v1 contract includes intervention response endpoint', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/services/contracts/v1Api.js'), 'utf-8')
  assert.equal(source.includes('respondIntervention: (interventionId, payload) =>'), true)
  assert.equal(source.includes('/api/v1/chat/interventions/${interventionId}/response'), true)
})
