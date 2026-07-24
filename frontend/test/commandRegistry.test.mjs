import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  executeCommand,
  getRegisteredCommands,
  isCommand,
  parseCommand,
} from '../src/services/commandRegistry.js'

test('command registry recognizes slash command input and parses args', () => {
  assert.equal(isCommand('/shape sales'), true)
  assert.equal(isCommand('shape sales'), false)

  const parsed = parseCommand('/percentile sales.amount 90')
  assert.equal(parsed?.name, 'percentile')
  assert.equal(parsed?.rawArgs, 'sales.amount 90')
  assert.deepEqual(parsed?.args, ['sales.amount', '90'])
})

test('command registry preloads EDA command catalog entries', () => {
  const commands = getRegisteredCommands()
  const names = commands.map((item) => item.name)

  assert.equal(names.includes('describe'), true)
  assert.equal(names.includes('mean'), true)
  assert.equal(names.includes('value_counts'), true)
  assert.equal(names.includes('nulls'), true)
  assert.equal(names.includes('help'), true)
})

test('executeCommand dispatches to backend endpoint with workspace context', async () => {
  const captured = {}
  const mockExecutionApi = {
    async command(workspaceId, payload) {
      captured.workspaceId = workspaceId
      captured.payload = payload
      return {
        name: 'shape',
        output: '/shape executed for table sales.',
        result_type: 'table',
        result: {
          columns: ['row_count', 'column_count'],
          data: [{ row_count: 3, column_count: 2 }],
          row_count: 1,
          result_type: 'table',
        },
      }
    },
  }

  const result = await executeCommand('/shape sales', {
    workspaceStore: {
      activeWorkspaceId: 'ws-1',
      activeWorkspaceSummary: { table_names: ['sales'] },
      columnCatalog: [],
    },
    conversationStore: {
      activeConversationId: 'conv-1',
    },
    executionApi: mockExecutionApi,
  })

  assert.equal(captured.workspaceId, 'ws-1')
  assert.equal(captured.payload?.name, 'shape')
  assert.equal(captured.payload?.default_table, 'sales')
  assert.equal(captured.payload?.conversation_id, 'conv-1')
  assert.equal(result?.name, 'shape')
  assert.equal(result?.result_type, 'table')
})

test('executeCommand reports when the native command bridge is unavailable', async () => {
  await assert.rejects(
    executeCommand('/shape sales', {
      workspaceStore: {
        activeWorkspaceId: 'ws-1',
        activeWorkspaceSummary: { table_names: ['sales'] },
        columnCatalog: [],
      },
    }),
    /desktop bridge is unavailable/,
  )
})

test('chat input routes slash commands through the command handler path', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('import { executeCommand, getRegisteredCommands, isCommand } from'), true)
  assert.equal(source.includes("import { executionApi } from '../../api/execution'"), true)
  assert.equal(source.includes('if (isCommand(questionText)) {'), true)
  assert.equal(source.includes('await handleSlashCommand(questionText)'), true)
  assert.equal(source.includes('const result = await executeCommand(questionText'), true)
  assert.equal(source.includes("conversationStore.addChatMessage(questionText, 'Running command...', { conversationId: requestConversationId })"), true)
  assert.equal(source.includes('getRegisteredCommands()'), true)
})
