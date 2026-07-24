import { normalizePlotlyFigure } from '../utils/figurePayload.js'
import { useArtifactStore } from '../stores/artifactStore'
import { useConversationStore } from '../stores/conversationStore'
import { useUiStore } from '../stores/uiStore'
import { useWorkspaceStore } from '../stores/workspaceStore'

function promotedId(prefix: string, runId: unknown, outputId: unknown) {
  const safe = `${runId || 'run'}-${outputId || 'output'}`
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return `${prefix}-${safe || Date.now().toString(36)}`
}

export function useArtifactPresentation() {
  const artifacts = useArtifactStore()
  const conversations = useConversationStore()
  const ui = useUiStore()
  const workspaces = useWorkspaceStore()

  function revealArtifactsPane(payload: Record<string, unknown> = {}) {
    if (payload.hasFigures === true) ui.setDataPane('figure')
    else if (payload.hasDataframes === true) ui.setDataPane('table')
    else if (payload.hasOutput === true) ui.setDataPane('output')
    return ui.dataPane
  }

  function resultScope() {
    return conversations.activeConversationId
      ? `conversation:${conversations.activeConversationId}`
      : `workspace:${workspaces.activeWorkspaceId || 'unscoped'}`
  }

  function promoteUserRunTable(outputValue: unknown, options: Record<string, unknown> = {}) {
    if (!outputValue || typeof outputValue !== 'object') return ''
    const output = outputValue as Record<string, any>
    const runId = String(options.runId || output.runId || output.run_id || '').trim()
    const outputId = String(options.outputId || output.id || options.index || '1').trim()
    const artifactId = promotedId('user-table', runId, outputId)
    const rawData = output.data && typeof output.data === 'object' ? output.data : output
    const logicalName = String(rawData.logical_name || output.logical_name || output.name || 'user_table').trim()
    const promoted = {
      ...output,
      name: logicalName,
      origin: 'user',
      promoted: true,
      scopeKey: resultScope(),
      sourceRunId: runId,
      data: {
        ...rawData,
        artifact_id: artifactId,
        source_artifact_id: rawData.artifact_id || output.artifact_id || undefined,
        logical_name: logicalName,
        display_name: `User revision · ${String(rawData.display_name || logicalName).trim()}`,
      },
    }
    artifacts.promotedUserDataframes = [
      promoted,
      ...artifacts.promotedUserDataframes.filter((item: any) => item?.data?.artifact_id !== artifactId),
    ]
    if (workspaces.activeWorkspaceId) {
      artifacts.setSelectedTableArtifact(workspaces.activeWorkspaceId, artifactId, conversations.activeTurnId)
    }
    artifacts.setResultData(promoted.data)
    ui.setDataPane('table')
    return artifactId
  }

  function promoteUserRunFigure(outputValue: unknown, options: Record<string, unknown> = {}) {
    if (!outputValue || typeof outputValue !== 'object') return ''
    const output = outputValue as Record<string, any>
    const runId = String(options.runId || output.runId || output.run_id || '').trim()
    const outputId = String(options.outputId || output.id || options.index || '1').trim()
    const artifactId = promotedId('user-chart', runId, outputId)
    const figure = normalizePlotlyFigure(output.data ?? output)
    if (!figure) return ''
    const logicalName = String(output.logical_name || output.name || 'user_chart').trim()
    const promoted = {
      ...output,
      name: logicalName,
      artifact_id: artifactId,
      logical_name: logicalName,
      display_name: `User revision · ${String(output.display_name || logicalName).trim()}`,
      origin: 'user',
      promoted: true,
      scopeKey: resultScope(),
      sourceRunId: runId,
      data: figure,
    }
    artifacts.promotedUserFigures = [
      promoted,
      ...artifacts.promotedUserFigures.filter((item: any) => item?.artifact_id !== artifactId),
    ]
    if (workspaces.activeWorkspaceId) {
      artifacts.setSelectedFigureArtifact(workspaces.activeWorkspaceId, artifactId, conversations.activeTurnId)
    }
    artifacts.setPlotlyFigure(figure)
    ui.setDataPane('figure')
    return artifactId
  }

  return { revealArtifactsPane, promoteUserRunTable, promoteUserRunFigure }
}
