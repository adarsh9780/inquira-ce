import { effectScope, nextTick } from 'vue'
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useActiveTurnCodeHydration } from '../src/composables/useActiveTurnCodeHydration'
import { useConversationStore } from '../src/stores/conversationStore'
import { useExecutionStore } from '../src/stores/executionStore'

describe('active turn code hydration', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('loads generated code when a persisted turn becomes active without executing it', async () => {
    const conversationStore = useConversationStore()
    const executionStore = useExecutionStore()
    conversationStore.setActiveConversationId('conversation-a')
    conversationStore.setActiveTurnPayload({
      id: 'turn-1',
      code_snapshot: 'result = conn.sql("SELECT 1").df()',
    })

    const scope = effectScope()
    scope.run(() => useActiveTurnCodeHydration())
    await nextTick()

    expect(executionStore.generatedCode).toBe('result = conn.sql("SELECT 1").df()')
    expect(executionStore.pythonFileContent).toBe('result = conn.sql("SELECT 1").df()')
    expect(executionStore.isCodeRunning).toBe(false)
    scope.stop()
  })

  it('preserves user edits when rehydrating the same generated-code baseline', async () => {
    const conversationStore = useConversationStore()
    const executionStore = useExecutionStore()
    conversationStore.setActiveConversationId('conversation-a')
    conversationStore.setActiveTurnPayload({ id: 'turn-1', code_snapshot: 'print("agent")' })
    executionStore.setGeneratedCode('print("agent")')
    executionStore.noteUserEditedCode('print("user")')

    const scope = effectScope()
    scope.run(() => useActiveTurnCodeHydration())
    await nextTick()

    expect(executionStore.pythonFileContent).toBe('print("user")')
    expect(executionStore.hasUserEditedCode).toBe(true)
    scope.stop()
  })
})
