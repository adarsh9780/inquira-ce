import test from 'node:test'
import assert from 'node:assert/strict'
import { parseSseBuffer } from '../src/utils/sseParser.js'

test('parseSseBuffer parses complete SSE events and leaves remainder', () => {
  const input = [
    'event: status',
    'data: {"message":"Starting"}',
    '',
    'event: node',
    'data: {"node":"check_safety"}',
    '',
    'event: final',
    'data: {"is_safe":true}',
    '',
    ''
  ].join('\n')

  const { events, remainder } = parseSseBuffer(input)
  assert.equal(remainder, '')
  assert.equal(events.length, 3)
  assert.equal(events[0].event, 'status')
  assert.equal(events[0].data.message, 'Starting')
  assert.equal(events[2].event, 'final')
  assert.equal(events[2].data.is_safe, true)
})

test('parseSseBuffer preserves incomplete tail', () => {
  const input = 'event: status\ndata: {"message":"Partial"}\n\nevent: node\ndata: {"node":"create'
  const { events, remainder } = parseSseBuffer(input)
  assert.equal(events.length, 1)
  assert.equal(events[0].event, 'status')
  assert.ok(remainder.startsWith('event: node'))
})

test('parseSseBuffer preserves spacing in plain-text token chunks', () => {
  const input = [
    'event: token',
    'data: {"text":"Hello "}',
    '',
    'event: token',
    'data: {"text":"world"}',
    '',
    ''
  ].join('\n')

  const { events } = parseSseBuffer(input)
  assert.equal(events.length, 2)
  assert.equal(events[0].data.text, 'Hello ')
  assert.equal(events[1].data.text, 'world')
})
