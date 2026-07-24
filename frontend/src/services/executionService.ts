import { executionApi } from '../api/execution.ts'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useConversationStore } from '../stores/conversationStore'
import { extractApiErrorMessage } from '../utils/apiError'
import { mapExecutionServiceResponse } from '../utils/executionServiceMapper'

class ExecutionService {
    async executePython(code: unknown): Promise<ReturnType<typeof mapExecutionServiceResponse>> {
        try {
            const workspaceStore = useWorkspaceStore()
            const conversationStore = useConversationStore()
            const response = await executionApi.runCode({
                code,
                timeout: 60,
                workspaceId: workspaceStore.activeWorkspaceId || null,
                conversationId: conversationStore.activeConversationId || '',
                parentTurnId: conversationStore.activeTurnId || '',
            })
            return mapExecutionServiceResponse(response)
        } catch (error: unknown) {
            return mapExecutionServiceResponse({
                success: false,
                error: extractApiErrorMessage(error, 'Execution failed'),
            })
        }
    }

}

const executionService = new ExecutionService()
export default executionService
