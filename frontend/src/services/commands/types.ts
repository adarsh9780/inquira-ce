export type CommandCategory =
  | 'overview'
  | 'column_stats'
  | 'distribution'
  | 'quality'
  | 'help'
  | 'custom'

export interface CommandDefinition {
  name: string
  usage: string
  description: string
  category: CommandCategory
}
