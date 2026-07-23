import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConversationStore = defineStore('conversations', () => {
  const chatHistory = ref<unknown[]>([])
  const questionHistory = ref<string[]>([])
  const currentQuestion = ref('')
  const liveTokenUsage = ref<Record<string, unknown> | null>(null)
  const activeConversationUsage = ref<Record<string, unknown> | null>(null)
  const conversationUsageById = ref<Record<string, unknown>>({})
  const conversations = ref<unknown[]>([])
  const activeConversationId = ref('')
  const conversationStateById = ref<Record<string, unknown>>({})
  const activeTurnId = ref('')
  const activeTurn = ref<Record<string, unknown> | null>(null)
  const activeTurnCode = ref('')
  const activeTurnRelations = ref<Record<string, unknown> | null>(null)
  const workspaceTurnTree = ref<Record<string, unknown> | null>(null)
  const finalTurnId = ref('')

  return {
    chatHistory,
    questionHistory,
    currentQuestion,
    liveTokenUsage,
    activeConversationUsage,
    conversationUsageById,
    conversations,
    activeConversationId,
    conversationStateById,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnRelations,
    workspaceTurnTree,
    finalTurnId,
  }
})
