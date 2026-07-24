import { overviewCommands } from './commands/overview.ts'
import { columnStatsCommands } from './commands/columnStats.ts'
import { distributionCommands } from './commands/distribution.ts'
import { qualityCommands } from './commands/quality.ts'
import { helpCommands } from './commands/help.ts'
import type { CommandDefinition } from './commands/types.ts'
import { executionApi } from '../api/execution.ts'

type RecordValue = Record<string, unknown>

export interface ParsedCommand {
  name: string
  rawArgs: string
  args: string[]
  rawCommand: string
  text: string
}

interface WorkspaceStoreLike {
  activeWorkspaceId?: unknown
  activeWorkspaceSummary?: {
    table_names?: unknown[]
  } | null
  columnCatalog?: Array<{ table_name?: unknown }>
}

interface ConversationStoreLike {
  activeConversationId?: unknown
}

interface CommandApi {
  command(workspaceId: unknown, payload: RecordValue): Promise<RecordValue>
}

interface ExecuteCommandOptions {
  workspaceStore?: WorkspaceStoreLike
  conversationStore?: ConversationStoreLike
  executionApi?: CommandApi
  executionService?: unknown
}

const commandRegistry = new Map<string, CommandDefinition>()

function normalizeCommandName(raw: unknown): string {
  return String(raw || '').trim().replace(/^\/+/, '').toLowerCase()
}

function parseArgs(rawArgs: unknown): string[] {
  const input = String(rawArgs || '').trim()
  if (!input) return []

  const tokens: string[] = []
  const tokenPattern = /"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|(\S+)/g

  let match = tokenPattern.exec(input)
  while (match) {
    const token = match[1] ?? match[2] ?? match[3] ?? ''
    if (token) tokens.push(token)
    match = tokenPattern.exec(input)
  }

  return tokens
}

export function registerCommand(definition: CommandDefinition): void {
  const normalizedName = normalizeCommandName(definition.name)
  if (!normalizedName) {
    throw new Error('Command definition requires a valid name')
  }

  commandRegistry.set(normalizedName, {
    name: normalizedName,
    usage: String(definition.usage || `/${normalizedName}`),
    description: String(definition.description || ''),
    category: definition.category || 'custom',
  })
}

export function isCommand(text: unknown): boolean {
  return /^\s*\/[a-zA-Z_]/.test(String(text || ''))
}

export function parseCommand(text: unknown): ParsedCommand | null {
  if (!isCommand(text)) return null

  const trimmed = String(text || '').trim()
  const firstWhitespace = trimmed.search(/\s/)
  const rawCommand = firstWhitespace === -1 ? trimmed : trimmed.slice(0, firstWhitespace)
  const rawArgs = firstWhitespace === -1 ? '' : trimmed.slice(firstWhitespace + 1).trim()
  const name = normalizeCommandName(rawCommand)

  if (!name) return null
  return {
    name,
    rawArgs,
    args: parseArgs(rawArgs),
    rawCommand: rawCommand.startsWith('/') ? rawCommand : `/${rawCommand}`,
    text: trimmed,
  }
}

export function getRegisteredCommands(): CommandDefinition[] {
  return Array.from(commandRegistry.values()).sort((left, right) => left.name.localeCompare(right.name))
}

function resolveDefaultTable(workspaceStore?: WorkspaceStoreLike): string | null {
  const summaryTable = (Array.isArray(workspaceStore?.activeWorkspaceSummary?.table_names)
    ? workspaceStore.activeWorkspaceSummary.table_names
    : []
  ).map((name) => String(name || '').trim()).find(Boolean)
  if (summaryTable) return summaryTable
  const catalogItem = (Array.isArray(workspaceStore?.columnCatalog) ? workspaceStore.columnCatalog : [])
    .find((item) => String(item?.table_name || '').trim())
  return String(catalogItem?.table_name || '').trim() || null
}

export async function executeCommand(text: unknown, {
  workspaceStore,
  conversationStore,
  executionApi: api = executionApi,
}: ExecuteCommandOptions = {}): Promise<RecordValue> {
  const parsed = parseCommand(text)
  if (!parsed) {
    throw new Error('Input is not a slash command.')
  }

  const commandDef = commandRegistry.get(parsed.name)
  if (!commandDef) {
    throw new Error(`Unknown command '/${parsed.name}'. Run /help to see available commands.`)
  }

  const workspaceId = String(workspaceStore?.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    throw new Error('Create/select a workspace before running commands.')
  }

  const response = await api.command(workspaceId, {
    text: parsed.text,
    name: parsed.name,
    raw_args: parsed.rawArgs,
    default_table: resolveDefaultTable(workspaceStore),
    conversation_id: String(conversationStore?.activeConversationId || '').trim() || null,
  })

  return {
    ...commandDef,
    parsed,
    ...response,
  }
}

;[
  ...overviewCommands,
  ...columnStatsCommands,
  ...distributionCommands,
  ...qualityCommands,
  ...helpCommands,
].forEach((definition) => registerCommand(definition))
