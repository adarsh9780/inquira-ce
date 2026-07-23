import apiService from './apiService'
import { useAppStore } from '../stores/appStore'
import { extractApiErrorMessage } from '../utils/apiError'
import { mapExecutionServiceResponse } from '../utils/executionServiceMapper'

class ExecutionService {
    async executePython(code) {
        try {
            const appStore = useAppStore()
            const response = await apiService.executeCode(
                code,
                60,
                appStore.activeWorkspaceId || null,
            )
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
