import { ref } from 'vue'
import type { useExecutionStore } from '../stores/executionStore'

type ExecutionStore = ReturnType<typeof useExecutionStore>

export function useConversationRunControl(execution: ExecutionStore) {
  const stoppedConversationIds = ref(new Set<string>())

  function stopConversation(conversationId: unknown) {
    const id = String(conversationId || '').trim()
    if (!id) return false
    stoppedConversationIds.value = new Set([...stoppedConversationIds.value, id])
    return execution.abortConversationRun(id)
  }

  function wasStopped(conversationId: unknown) {
    return stoppedConversationIds.value.has(String(conversationId || '').trim())
  }

  function clearStopped(conversationId: unknown) {
    const id = String(conversationId || '').trim()
    const next = new Set(stoppedConversationIds.value)
    next.delete(id)
    stoppedConversationIds.value = next
  }

  return { stoppedConversationIds, stopConversation, wasStopped, clearStopped }
}
