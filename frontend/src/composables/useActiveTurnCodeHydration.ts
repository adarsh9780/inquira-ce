import { watch } from 'vue'
import { useConversationStore } from '../stores/conversationStore'
import { useExecutionStore } from '../stores/executionStore'

export function useActiveTurnCodeHydration() {
  const conversationStore = useConversationStore()
  const executionStore = useExecutionStore()

  function hydrateActiveTurnCode() {
    const turnId = String(conversationStore.activeTurnId || '').trim()
    if (!turnId) return

    const generatedCode = String(conversationStore.activeTurnCode || '')
    const sameAgentBaseline = generatedCode === String(executionStore.generatedCode || '')
    if (sameAgentBaseline && (executionStore.hasUserEditedCode || executionStore.pythonFileContent)) return

    executionStore.setGeneratedCode(generatedCode)
  }

  watch(
    () => [
      String(conversationStore.activeConversationId || '').trim(),
      String(conversationStore.activeTurnId || '').trim(),
      String(conversationStore.activeTurnCode || ''),
    ].join('\u0000'),
    hydrateActiveTurnCode,
    { immediate: true },
  )

  return { hydrateActiveTurnCode }
}
