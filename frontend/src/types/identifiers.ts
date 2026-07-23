declare const identifierBrand: unique symbol

export type Identifier<Name extends string> = string & {
  readonly [identifierBrand]: Name
}

export type WorkspaceId = Identifier<'WorkspaceId'>
export type ConnectionId = Identifier<'ConnectionId'>
export type ConversationId = Identifier<'ConversationId'>
export type TurnId = Identifier<'TurnId'>
export type RunId = Identifier<'RunId'>
export type ArtifactId = Identifier<'ArtifactId'>
export type TerminalSessionId = Identifier<'TerminalSessionId'>
