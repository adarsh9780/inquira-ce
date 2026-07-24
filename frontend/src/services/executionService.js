import { executionApi } from '../api/execution.ts'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useConversationStore } from '../stores/conversationStore'
import { extractApiErrorMessage } from '../utils/apiError'
import { mapExecutionServiceResponse } from '../utils/executionServiceMapper'

class ExecutionService {
    async executePython(code) {
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
        } catch (err) {
            return {
                success: false,
                stdout: '',
                stderr: '',
                error: extractApiErrorMessage(err, 'Execution failed'),
                result: null,
                resultType: null,
                runId: null,
                artifacts: [],
                variables: { dataframes: {}, figures: {}, scalars: {} },
            }
        }
    }

}

const executionService = new ExecutionService()
export default executionService
