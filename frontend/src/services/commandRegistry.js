import { overviewCommands } from './commands/overview.js'
import { columnStatsCommands } from './commands/columnStats.js'
import { distributionCommands } from './commands/distribution.js'
import { qualityCommands } from './commands/quality.js'
import { helpCommands } from './commands/help.js'

const commandRegistry = new Map()

function normalizeCommandName(raw) {
  return String(raw || '').trim().replace(/^\/+/, '').toLowerCase()
}

function parseArgs(rawArgs) {
  const input = String(rawArgs || '').trim()
  if (!input) return []

  const tokens = []
  const tokenPattern = /"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|(\S+)/g

  let match = tokenPattern.exec(input)
  while (match) {
    const token = match[1] ?? match[2] ?? match[3] ?? ''
    if (token) tokens.push(token)
    match = tokenPattern.exec(input)
  }

  return tokens
}

export function registerCommand(definition) {
  const normalizedName = normalizeCommandName(definition?.name)
  if (!normalizedName) {
    throw new Error('Command definition requires a valid name')
  }

  commandRegistry.set(normalizedName, {
    name: normalizedName,
    usage: String(definition?.usage || `/${normalizedName}`),
    description: String(definition?.description || ''),
    category: String(definition?.category || 'custom'),
  })
}

export function isCommand(text) {
  return /^\s*\/[a-zA-Z_]/.test(String(text || ''))
}

export function parseCommand(text) {
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

export function getRegisteredCommands() {
  return Array.from(commandRegistry.values()).sort((left, right) => left.name.localeCompare(right.name))
}

export async function executeCommand(text, { appStore, apiService: api = null } = {}) {
  const parsed = parseCommand(text)
  if (!parsed) {
    throw new Error('Input is not a slash command.')
  }

  const commandDef = commandRegistry.get(parsed.name)
  if (!commandDef) {
    throw new Error(`Unknown command '/${parsed.name}'. Run /help to see available commands.`)
  }

  const workspaceId = String(appStore?.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    throw new Error('Create/select a workspace before running commands.')
  }

  let resolvedApi = api
  if (!resolvedApi) {
    const apiModule = await import('./apiService.js')
    resolvedApi = apiModule.default
  }

  const response = await resolvedApi.v1ExecuteWorkspaceCommand(workspaceId, {
    text: parsed.text,
    name: parsed.name,
    raw_args: parsed.rawArgs,
    default_table: String(appStore?.ingestedTableName || '').trim() || null,
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
