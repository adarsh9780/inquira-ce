import type { ConversationId, RunId, TerminalSessionId, WorkspaceId } from './identifiers'

export type RuntimeState =
  | { state: 'unavailable'; message?: string }
  | { state: 'starting'; startedAt: number; message?: string }
  | { state: 'ready'; pythonExecutable?: string }
  | { state: 'busy'; operationId: string; message?: string }
  | { state: 'failed'; message: string; recoverable: boolean }

export type OperationState =
  | { state: 'queued'; id: string; label: string }
  | { state: 'running'; id: string; label: string; startedAt: number }
  | { state: 'succeeded'; id: string; label: string; completedAt: number }
  | { state: 'failed'; id: string; label: string; message: string }
  | { state: 'cancelled'; id: string; label: string }

export interface ExecutionRecord {
  id: RunId
  workspace_id: WorkspaceId
  conversation_id?: ConversationId
  code: string
  stdout?: string
  stderr?: string
  success: boolean
  started_at?: string
  completed_at?: string
}

export interface TerminalEntry {
  id: string
  session_id?: TerminalSessionId
  kind: 'input' | 'output' | 'error' | 'system'
  text: string
  created_at: string
}
