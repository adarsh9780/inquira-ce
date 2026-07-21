import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiService } from '../src/services/apiService'

afterEach(() => {
  delete window.go
  delete window.runtime
})

describe('native analysis bridge', () => {
  it('routes conversations and a streamed analysis through Wails', async () => {
    let runtimeCallback = null
    const cancelEvents = vi.fn()
    window.runtime = {
      EventsOnMultiple: vi.fn((_name, callback) => {
        runtimeCallback = callback
        return cancelEvents
      }),
    }
    const app = {
      CreateConversation: vi.fn().mockResolvedValue({ id: 'conversation-1', workspace_id: 'workspace-1' }),
      ListConversations: vi.fn().mockResolvedValue([{ id: 'conversation-1', workspace_id: 'workspace-1' }]),
      ListConversationTurns: vi.fn().mockResolvedValue([]),
      AnalyzeQuestion: vi.fn(async (request) => {
        runtimeCallback({ client_request_id: 'another-request', type: 'agent_status', data: { stage: 'generating' } })
        runtimeCallback({ client_request_id: request.client_request_id, type: 'agent_status', data: { stage: 'executing' } })
        return {
          conversation: { id: 'conversation-1', workspace_id: 'workspace-1' },
          turn: { id: 'turn-1', conversation_id: 'conversation-1' },
          answer: 'Total sales are 42.',
          code: "result = conn.execute('SELECT 42 AS total').df()",
          run_id: 'run-1',
          execution: {
            success: true,
            result_kind: 'dataframe',
            result: { columns: ['total'], rows: [{ total: 42 }] },
            artifacts: [],
          },
          artifacts: [{ id: 'artifact-1', kind: 'dataframe', logical_name: 'result' }],
          metadata: { token_usage: { total_tokens: 25 } },
          route: 'analysis',
        }
      }),
    }
    window.go = { main: { App: app } }

    const created = await apiService.v1CreateConversation('workspace-1', 'Question')
    const listed = await apiService.v1ListConversations('workspace-1')
    const events = []
    const result = await apiService.v1AnalyzeStream({
      workspace_id: 'workspace-1', conversation_id: 'conversation-1',
      selected_parent_turn_id: 'parent-1', question: 'What are total sales?', current_code: 'result = previous',
      attachments: [{ attachment_id: 'image-1', media_type: 'image/png', filename: 'chart.png', data_base64: 'aW1hZ2U=' }],
    }, { onEvent: (event) => events.push(event) })

    expect(created.id).toBe('conversation-1')
    expect(listed).toEqual({ conversations: [{ id: 'conversation-1', workspace_id: 'workspace-1' }] })
    expect(app.AnalyzeQuestion).toHaveBeenCalledWith({
      client_request_id: expect.any(String),
      workspace_id: 'workspace-1', conversation_id: 'conversation-1',
      parent_turn_id: 'parent-1', question: 'What are total sales?', current_code: 'result = previous', timeout_seconds: 360,
      attachments: [{ attachment_id: 'image-1', media_type: 'image/png', filename: 'chart.png', data_base64: 'aW1hZ2U=' }],
    })
    expect(events).toEqual([{ event: 'agent_status', data: { stage: 'executing', message: 'Running analysis code…' } }])
    expect(result).toMatchObject({
      conversation_id: 'conversation-1', turn_id: 'turn-1', is_safe: true,
      explanation: 'Total sales are 42.', run_id: 'run-1',
      result: { columns: ['total'], data: [{ total: 42 }] },
      artifacts: [{ id: 'artifact-1', artifact_id: 'artifact-1' }],
      metadata: { token_usage: { total_tokens: 25 } }, route: 'analysis',
    })
    expect(cancelEvents).toHaveBeenCalledOnce()
  })

  it('cancels only the native request that owns the abort signal', async () => {
    const app = {
      AnalyzeQuestion: vi.fn(() => new Promise(() => {})),
      CancelAgentAnalysis: vi.fn().mockResolvedValue(true),
      InterruptWorkspaceKernel: vi.fn().mockResolvedValue(true),
    }
    window.go = { main: { App: app } }
    const controller = new AbortController()
    const pending = apiService.v1AnalyzeStream({
      workspace_id: 'workspace-1', question: 'Stop this request',
    }, { signal: controller.signal })

    await vi.waitFor(() => expect(app.AnalyzeQuestion).toHaveBeenCalledOnce())
    const request = app.AnalyzeQuestion.mock.calls[0][0]
    controller.abort()
    await expect(pending).rejects.toBeTruthy()
    expect(app.CancelAgentAnalysis).toHaveBeenCalledWith('workspace-1', request.client_request_id)
    expect(app.InterruptWorkspaceKernel).not.toHaveBeenCalled()
  })

  it('submits intervention choices through the native worker binding', async () => {
    const app = {
      RespondAgentIntervention: vi.fn().mockResolvedValue({ intervention_id: 'intervention-1', accepted: true }),
    }
    window.go = { main: { App: app } }
    const result = await apiService.v1RespondChatIntervention('intervention-1', ['approve'])
    expect(app.RespondAgentIntervention).toHaveBeenCalledWith('intervention-1', ['approve'])
    expect(result).toEqual({ intervention_id: 'intervention-1', accepted: true })
  })
})
