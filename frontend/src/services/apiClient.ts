import { getInquira } from './generatedApi'

const generated = getInquira()

type Args<T extends (...args: never[]) => unknown> = Parameters<T>

export const CHAT_STREAM_PATH = '/api/v1/chat/stream'

/**
 * Product-facing names over the generated OpenAPI client.
 *
 * This adapter contains no handwritten HTTP paths. Its argument and response
 * contracts are inferred from the generated client so regeneration remains the
 * single source of truth for request shapes.
 */
export const domainApi = {
  auth: {
    config: (options?: Args<typeof generated.getAuthConfigApiV1AuthConfigGet>[0]) =>
      generated.getAuthConfigApiV1AuthConfigGet(options),
    me: (options?: Args<typeof generated.getCurrentUserProfileApiV1AuthMeGet>[0]) =>
      generated.getCurrentUserProfileApiV1AuthMeGet(options),
    logout: () => generated.logoutUserApiV1AuthLogoutPost(),
  },
  workspaces: {
    list: () => generated.listWorkspacesApiV1WorkspacesGet(),
    create: (name: string, schemaContext = '') =>
      generated.createWorkspaceApiV1WorkspacesPost({ name, schema_context: schemaContext }),
    activate: (workspaceId: string) =>
      generated.activateWorkspaceApiV1WorkspacesWorkspaceIdActivatePut(workspaceId),
    summary: (workspaceId: string) =>
      generated.getWorkspaceSummaryApiV1WorkspacesWorkspaceIdSummaryGet(workspaceId),
    aiConfig: (workspaceId: string) =>
      generated.getWorkspaceAiConfigApiV1WorkspacesWorkspaceIdAiConfigGet(workspaceId),
    updateAiConfig: (
      workspaceId: string,
      payload: Args<typeof generated.updateWorkspaceAiConfigApiV1WorkspacesWorkspaceIdAiConfigPut>[1],
    ) => generated.updateWorkspaceAiConfigApiV1WorkspacesWorkspaceIdAiConfigPut(workspaceId, payload),
    resetAiConfig: (workspaceId: string) =>
      generated.resetWorkspaceAiConfigApiV1WorkspacesWorkspaceIdAiConfigOverridesDelete(workspaceId),
    rename: (workspaceId: string, name?: string | null, schemaContext?: string) => {
      const payload: Args<typeof generated.renameWorkspaceApiV1WorkspacesWorkspaceIdPatch>[1] = {}
      if (name !== null && name !== undefined) payload.name = name
      if (schemaContext !== undefined) payload.schema_context = schemaContext
      return generated.renameWorkspaceApiV1WorkspacesWorkspaceIdPatch(workspaceId, payload)
    },
    clearDatabase: (workspaceId: string) =>
      generated.clearWorkspaceDatabaseApiV1WorkspacesWorkspaceIdDatabaseClearPost(workspaceId),
    remove: (workspaceId: string) =>
      generated.deleteWorkspaceApiV1WorkspacesWorkspaceIdDelete(workspaceId),
    deletions: () => generated.listWorkspaceDeletionsApiV1WorkspacesDeletionsGet(),
    deletionById: (jobId: string) =>
      generated.getWorkspaceDeletionApiV1WorkspacesDeletionsJobIdGet(jobId),
  },
  datasets: {
    list: (workspaceId: string) =>
      generated.listWorkspaceDatasetsApiV1WorkspacesWorkspaceIdDatasetsGet(workspaceId),
    add: (workspaceId: string, sourcePath: string) =>
      generated.addWorkspaceDatasetApiV1WorkspacesWorkspaceIdDatasetsPost(workspaceId, { source_path: sourcePath }),
    addBatch: (workspaceId: string, sourcePaths: string[]) =>
      generated.addWorkspaceDatasetsBatchApiV1WorkspacesWorkspaceIdDatasetsBatchPost(
        workspaceId,
        { source_paths: sourcePaths },
      ),
    remove: (workspaceId: string, tableName: string) =>
      generated.removeWorkspaceDatasetApiV1WorkspacesWorkspaceIdDatasetsTableNameDelete(workspaceId, tableName),
    ingestions: (workspaceId: string) =>
      generated.listWorkspaceDatasetIngestionsApiV1WorkspacesWorkspaceIdDatasetsIngestionsGet(workspaceId),
    resumeIngestions: (workspaceId: string) =>
      generated.resumeWorkspaceDatasetIngestionsApiV1WorkspacesWorkspaceIdDatasetsIngestionsResumePost(workspaceId),
    ingestionById: (workspaceId: string, jobId: string) =>
      generated.getWorkspaceDatasetIngestionApiV1WorkspacesWorkspaceIdDatasetsIngestionsJobIdGet(workspaceId, jobId),
    deletions: (workspaceId: string) =>
      generated.listWorkspaceDatasetDeletionsApiV1WorkspacesWorkspaceIdDatasetsDeletionsGet(workspaceId),
    deletionById: (workspaceId: string, jobId: string) =>
      generated.getWorkspaceDatasetDeletionApiV1WorkspacesWorkspaceIdDatasetsDeletionsJobIdGet(workspaceId, jobId),
    enqueueSchemaRegeneration: (workspaceId: string, tableName: string) =>
      generated.enqueueWorkspaceDatasetSchemaRegenerationApiV1WorkspacesWorkspaceIdDatasetsTableNameSchemaEnqueuePost(
        workspaceId,
        tableName,
      ),
    syncBrowser: (
      workspaceId: string,
      payload: Args<typeof generated.syncBrowserWorkspaceDatasetApiV1WorkspacesWorkspaceIdDatasetsBrowserSyncPost>[1],
    ) => generated.syncBrowserWorkspaceDatasetApiV1WorkspacesWorkspaceIdDatasetsBrowserSyncPost(workspaceId, payload),
  },
  preferences: {
    get: (provider: string | null = null) =>
      generated.getPreferencesApiV1PreferencesGet(provider ? { params: { provider } } : undefined),
    update: (payload: Args<typeof generated.updatePreferencesApiV1PreferencesPut>[0]) =>
      generated.updatePreferencesApiV1PreferencesPut(payload),
    refreshModels: (payload: Args<typeof generated.refreshProviderModelsApiV1PreferencesModelsRefreshPost>[0]) =>
      generated.refreshProviderModelsApiV1PreferencesModelsRefreshPost(payload),
    searchModels: ({ provider, query, limit = 25 }: { provider: string; query: string; limit?: number }) =>
      generated.searchProviderModelsApiV1PreferencesModelsSearchGet({ provider, q: query, limit }),
    verifyKey: (provider: string, apiKey: string) =>
      generated.verifyApiKeyApiV1PreferencesVerifyKeyPost({ provider, api_key: apiKey }),
    setApiKey: (payload: Args<typeof generated.setApiKeyApiV1PreferencesApiKeyPut>[0]) =>
      generated.setApiKeyApiV1PreferencesApiKeyPut(payload),
    deleteApiKey: (provider = 'openrouter') =>
      generated.deleteApiKeyApiV1PreferencesApiKeyDelete({ provider }),
  },
  conversations: {
    list: (workspaceId: string, limit = 50) =>
      generated.listConversationsApiV1WorkspacesWorkspaceIdConversationsGet(workspaceId, { limit }),
    create: (workspaceId: string, title: string | null = null) =>
      generated.createConversationApiV1WorkspacesWorkspaceIdConversationsPost(workspaceId, { title }),
    remove: (conversationId: string) =>
      generated.deleteConversationApiV1ConversationsConversationIdDelete(conversationId),
    update: (
      conversationId: string,
      payload: Args<typeof generated.patchConversationApiV1ConversationsConversationIdPatch>[1],
    ) => generated.patchConversationApiV1ConversationsConversationIdPatch(conversationId, payload),
    usage: (conversationId: string) =>
      generated.getConversationUsageApiV1ConversationsConversationIdUsageGet(conversationId),
    turns: (
      conversationId: string,
      params: Args<typeof generated.listTurnsApiV1ConversationsConversationIdTurnsGet>[1],
    ) => generated.listTurnsApiV1ConversationsConversationIdTurnsGet(conversationId, params),
  },
  chat: {
    analyze: (payload: Args<typeof generated.analyzeApiV1ChatAnalyzePost>[0]) =>
      generated.analyzeApiV1ChatAnalyzePost(payload),
    stream: CHAT_STREAM_PATH,
    respondIntervention: (
      interventionId: string,
      payload: Args<typeof generated.respondToInterventionApiV1ChatInterventionsInterventionIdResponsePost>[1],
    ) => generated.respondToInterventionApiV1ChatInterventionsInterventionIdResponsePost(interventionId, payload),
  },
  runtime: {
    installRunnerPackage: (
      payload: Args<typeof generated.installRunnerRuntimePackageApiV1RuntimeRunnerPackagesInstallPost>[0],
    ) => generated.installRunnerRuntimePackageApiV1RuntimeRunnerPackagesInstallPost(payload),
    workspaceResourceRecommendation: () =>
      generated.getWorkspaceRuntimeResourceRecommendationApiV1WorkspaceRuntimeResourceRecommendationGet(),
    workspaceColumns: (workspaceId: string) =>
      generated.getWorkspaceColumnsApiV1WorkspacesWorkspaceIdColumnsGet(workspaceId),
    listWorkspaceCommands: (workspaceId: string) =>
      generated.listWorkspaceCommandsApiV1WorkspacesWorkspaceIdCommandsGet(workspaceId),
    executeWorkspaceCommand: (
      workspaceId: string,
      payload: Args<typeof generated.executeWorkspaceSlashCommandApiV1WorkspacesWorkspaceIdCommandsExecutePost>[1],
    ) => generated.executeWorkspaceSlashCommandApiV1WorkspacesWorkspaceIdCommandsExecutePost(workspaceId, payload),
    bootstrapWorkspaceRuntime: (workspaceId: string) =>
      generated.bootstrapWorkspaceRuntimeEndpointApiV1WorkspacesWorkspaceIdRuntimeBootstrapPost(workspaceId),
    retryWorkspaceRuntime: (workspaceId: string) =>
      generated.retryWorkspaceRuntimeEndpointApiV1WorkspacesWorkspaceIdRuntimeRetryPost(workspaceId),
    hardResetWorkspaceRuntime: (workspaceId: string) =>
      generated.hardResetWorkspaceRuntimeEndpointApiV1WorkspacesWorkspaceIdRuntimeHardResetPost(workspaceId),
    workspaceRuntimeStatus: (workspaceId: string) =>
      generated.getWorkspaceRuntimeStatusEndpointApiV1WorkspacesWorkspaceIdRuntimeStatusGet(workspaceId),
    workspaceRuntimeInterrupt: (workspaceId: string) =>
      generated.interruptWorkspaceRuntimeApiV1WorkspacesWorkspaceIdRuntimeInterruptPost(workspaceId),
    workspaceRuntimeReset: (workspaceId: string) =>
      generated.resetWorkspaceRuntimeApiV1WorkspacesWorkspaceIdRuntimeResetPost(workspaceId),
    workspaceRuntimeRestart: (workspaceId: string) =>
      generated.restartWorkspaceRuntimeApiV1WorkspacesWorkspaceIdRuntimeRestartPost(workspaceId),
  },
} as const
