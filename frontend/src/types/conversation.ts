import type { ConversationId, RunId, TurnId, WorkspaceId } from './identifiers'

export interface TokenUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens: number
}

export interface ConversationSummary {
  id: ConversationId
  workspace_id: WorkspaceId
  title: string
  created_at?: string
  updated_at?: string
  last_turn_at?: string
  final_turn_id?: TurnId
  usage?: TokenUsage
}

export interface ConversationTurn {
  id: TurnId
  conversation_id: ConversationId
  parent_turn_id?: TurnId | null
  seq_no?: number
  user_text: string
  assistant_text: string
  code?: string
  run_id?: RunId
  created_at?: string
  usage?: TokenUsage
  children?: ConversationTurn[]
}

export type StreamEvent =
  | { type: 'agent_status'; conversationId: ConversationId; stage: string; message?: string }
  | { type: 'assistant_token'; conversationId: ConversationId; text: string }
  | { type: 'reasoning'; conversationId: ConversationId; text: string }
  | { type: 'tool_started'; conversationId: ConversationId; toolCallId: string; name: string; input?: unknown }
  | { type: 'tool_finished'; conversationId: ConversationId; toolCallId: string; name: string; output?: unknown; durationMs?: number }
  | { type: 'usage'; conversationId: ConversationId; usage: TokenUsage }
  | { type: 'error'; conversationId: ConversationId; message: string; code?: string }

export type ConversationRunState =
  | { state: 'idle' }
  | { state: 'starting'; startedAt: number }
  | { state: 'streaming'; startedAt: number; message?: string }
  | { state: 'cancelling'; startedAt: number }
  | { state: 'failed'; startedAt: number; message: string }
  | { state: 'completed'; startedAt: number; completedAt: number }
