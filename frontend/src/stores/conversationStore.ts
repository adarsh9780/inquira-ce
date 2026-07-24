import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConversationStore = defineStore('conversation', () => {
  const chatHistory = ref<unknown[]>([])
  const questionHistory = ref<string[]>([])
  const currentQuestion = ref('')
  const currentExplanation = ref('')
  const liveTokenUsage = ref<unknown>(null)
  const activeConversationUsage = ref<unknown>(null)
  const conversationUsageById = ref<Record<string, unknown>>({})
  const conversations = ref<unknown[]>([])
  const activeConversationId = ref('')
  const conversationStateById = ref<Record<string, unknown>>({})
  const conversationRuns = ref<Record<string, unknown>>({})
  const turnViewEnabled = ref(true)
  const activeTurnId = ref('')
  const activeTurn = ref<unknown>(null)
  const activeTurnCode = ref('')
  const activeTurnArtifacts = ref<unknown[]>([])
  const activeTurnRelations = ref<unknown>(null)
  const activeTurnTree = ref<unknown>(null)
  const activeTurnArtifactRefreshKey = ref(0)
  const workspaceTurnTree = ref<unknown>(null)
  const finalTurnId = ref('')
  const turnsNextCursor = ref<string | null>(null)

  return {
    chatHistory,
    questionHistory,
    currentQuestion,
    currentExplanation,
    liveTokenUsage,
    activeConversationUsage,
    conversationUsageById,
    conversations,
    activeConversationId,
    conversationStateById,
    conversationRuns,
    turnViewEnabled,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnArtifacts,
    activeTurnRelations,
    activeTurnTree,
    activeTurnArtifactRefreshKey,
    workspaceTurnTree,
    finalTurnId,
    turnsNextCursor,
  }
})
