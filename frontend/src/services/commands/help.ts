import type { CommandDefinition } from './types'

export const helpCommands = [
  {
    name: 'help',
    usage: '/help [command]',
    description: 'List commands or show command usage',
    category: 'help',
  },
] satisfies readonly CommandDefinition[]
