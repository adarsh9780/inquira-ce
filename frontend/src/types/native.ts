export type NativeRecord = Record<string, unknown>

export interface NativeRowsRequest {
  offset: number
  limit: number
  sort_model: unknown[]
  filter_model: NativeRecord
  search_text: string
}

export interface NativeCreateConversationRequest {
  workspace_id: string
  title: string
}

export interface NativeAnalyzeRequest {
  client_request_id: string
  workspace_id: string
  conversation_id: string
  parent_turn_id: string | null
  question: string
  current_code: string
  timeout_seconds: number
  attachments: unknown[]
}

export interface NativeRunManualCodeRequest {
  workspace_id: string
  conversation_id: string
  parent_turn_id: string | null
  code: string
  timeout_seconds: number
}

export interface NativeCommandRequest {
  workspace_id: string
  conversation_id: string
  text: string
  name: string
  raw_args: string
  default_table: string
  row_limit: number
}

export interface NativeCreateWorkspaceRequest {
  name: string
  schema_context: string
}

export interface NativeUpdateWorkspaceRequest {
  workspace_id: string
  name: string
  schema_context?: string
}

export interface NativeSaveSchemaRequest {
  workspace_id: string
  table_name: string
  context?: string
  table_context?: string
  columns: unknown[]
}

export interface NativeSaveTableContextRequest {
  workspace_id: string
  table_name: string
  context: string
}

export interface NativeRegenerateSchemaRequest {
  workspace_id: string
  table_name: string
  context: string
  allow_sample_values: boolean
}

export interface NativeArtifactListResponse extends NativeRecord {
  artifacts?: unknown[]
  total?: number
}

export interface NativeSearchResponse extends NativeRecord {
  models?: unknown[]
}

export interface NativeMethodMap {
  ActivateWorkspace: (workspaceId: string) => Promise<NativeRecord>
  AnalyzeQuestion: (request: NativeAnalyzeRequest) => Promise<unknown>
  CancelAgentAnalysis: (workspaceId: string, clientRequestId: string) => Promise<boolean>
  CancelRuntimeProvisioning: () => Promise<boolean>
  ChooseCertificateBundle: () => Promise<string>
  ChooseLocalConnectionFile: () => Promise<unknown>
  ChoosePythonExecutable: () => Promise<string>
  CompleteModelOnboarding: () => Promise<NativeRecord>
  CreateConversation: (request: NativeCreateConversationRequest) => Promise<NativeRecord>
  CreateLocalConnection: (request: NativeRecord) => Promise<unknown>
  CreateWorkspace: (request: NativeCreateWorkspaceRequest) => Promise<NativeRecord>
  DeleteConnection: (connectionId: string) => Promise<unknown>
  DeleteConversation: (conversationId: string) => Promise<NativeRecord>
  DeleteConversationTurn: (conversationId: string, turnId: string) => Promise<NativeRecord>
  DeleteProviderAPIKey: (provider: string) => Promise<NativeRecord>
  DeleteTurnArtifact: (
    conversationId: string,
    turnId: string,
    artifactId: string,
  ) => Promise<NativeRecord>
  DeleteWorkspace: (workspaceId: string) => Promise<NativeRecord>
  DiscoverLocalConnection: (request: NativeRecord) => Promise<unknown>
  ExecuteWorkspaceCommand: (request: NativeCommandRequest) => Promise<NativeRecord>
  ExportRuntimeDiagnostics: () => Promise<boolean>
  GetConversationTurn: (turnId: string) => Promise<unknown>
  GetConversationUsage: (conversationId: string) => Promise<NativeRecord>
  GetFinalConversationTurn: (conversationId: string) => Promise<unknown>
  GetModelOnboardingStatus: () => Promise<NativeRecord>
  GetModelPreferences: (provider: string) => Promise<NativeRecord>
  GetStartupState: () => Promise<unknown>
  GetTermsAndConditions: () => Promise<NativeRecord>
  GetTurnArtifactMetadata: (
    conversationId: string,
    turnId: string,
    artifactId: string,
  ) => Promise<NativeRecord>
  GetTurnArtifactRows: (
    conversationId: string,
    turnId: string,
    artifactId: string,
    request: NativeRowsRequest,
  ) => Promise<unknown>
  GetWorkspaceAIConfig: (workspaceId: string) => Promise<NativeRecord>
  GetWorkspaceArtifactRows: (
    workspaceId: string,
    artifactId: string,
    request: NativeRowsRequest,
  ) => Promise<unknown>
  GetWorkspaceDatasetSchema: (workspaceId: string, tableName: string) => Promise<NativeRecord>
  GetWorkspaceKernelStatus: (workspaceId: string) => Promise<NativeRecord>
  GetWorkspaceSummary: (workspaceId: string) => Promise<NativeRecord>
  ListConnections: (workspaceId: string) => Promise<unknown>
  ListConversationTurnPage: (
    conversationId: string,
    limit: number,
    cursor: string,
  ) => Promise<NativeRecord>
  ListConversationTurns: (conversationId: string) => Promise<unknown[]>
  ListConversations: (workspaceId: string) => Promise<unknown>
  ListTurnArtifactSummaries: (
    conversationId: string,
    turnId: string,
    kind: string,
  ) => Promise<NativeArtifactListResponse>
  ListWorkspaceDatasets: (workspaceId: string) => Promise<NativeRecord>
  ListWorkspaces: () => Promise<unknown>
  LoadLocalState: (scope: string) => Promise<NativeRecord>
  MarkFinalConversationTurn: (conversationId: string, turnId: string) => Promise<unknown>
  OpenExternalURL: (url: string) => Promise<void>
  OpenStartupLogs: () => Promise<void>
  PreviewLocalConnection: (request: NativeRecord) => Promise<unknown>
  PreviewWorkspaceDataset: (
    workspaceId: string,
    tableName: string,
    mode: string,
  ) => Promise<NativeRecord>
  ProvisionRuntime: (configuration: NativeRecord) => Promise<unknown>
  RepairRuntime: () => Promise<unknown>
  RefreshConnection: (connectionId: string) => Promise<unknown>
  RefreshWorkspaceDatasetSources: (workspaceId: string) => Promise<NativeRecord>
  RefreshProviderModels: (request: NativeRecord) => Promise<NativeRecord>
  RegenerateWorkspaceDatasetSchema: (
    request: NativeRegenerateSchemaRequest,
  ) => Promise<NativeRecord>
  ResizeTerminalSession: (sessionId: string, columns: number, rows: number) => Promise<void>
  RestartDesktopApp: () => Promise<void>
  ResetRuntime: () => Promise<boolean>
  RollbackRuntime: () => Promise<unknown>
  RunManualCode: (request: NativeRunManualCodeRequest) => Promise<unknown>
  RuntimePlan: (configuration: NativeRecord) => Promise<unknown>
  RuntimeStatus: () => Promise<NativeRecord>
  SaveExportFile: (request: NativeRecord) => Promise<boolean>
  SaveLocalState: (scope: string, state: NativeRecord) => Promise<boolean>
  SaveProviderConfiguration: (request: NativeRecord) => Promise<NativeRecord>
  SaveWorkspaceDatasetSchema: (request: NativeSaveSchemaRequest) => Promise<NativeRecord>
  SaveWorkspaceDatasetContext: (
    request: NativeSaveTableContextRequest,
  ) => Promise<NativeRecord>
  SearchProviderModels: (
    provider: string,
    query: string,
    limit: number,
  ) => Promise<NativeSearchResponse | unknown[]>
  StartTerminalSession: (request: NativeRecord) => Promise<NativeRecord>
  StopTerminalSession: (sessionId: string) => Promise<unknown>
  UpdateConversation: (conversationId: string, title: string) => Promise<NativeRecord>
  UpdateModelPreferences: (request: NativeRecord) => Promise<NativeRecord>
  UpdateWorkspace: (request: NativeUpdateWorkspaceRequest) => Promise<NativeRecord>
  UpdateWorkspaceAIConfig: (
    workspaceId: string,
    request: NativeRecord,
  ) => Promise<NativeRecord>
  VerifyProviderAPIKey: (provider: string, apiKey: string) => Promise<NativeRecord>
  WriteTerminalSession: (sessionId: string, data: string) => Promise<void>
}

export type NativeMethodName = keyof NativeMethodMap
export type NativeMethod<Method extends NativeMethodName> = NativeMethodMap[Method]
export type NativeArguments<Method extends NativeMethodName> = Parameters<NativeMethod<Method>>
export type NativeResult<Method extends NativeMethodName> = Awaited<ReturnType<NativeMethod<Method>>>
export type NativeApp = Partial<NativeMethodMap>
