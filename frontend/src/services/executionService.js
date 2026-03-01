/**
 * executionService.js — Server-Side Code Execution
 *
 * Drop-in replacement for the legacy in-browser Python execution service.
 * Instead of running Python in the browser,
 * this service sends code to the backend for execution and returns results.
 *
 * The API contract is intentionally kept stable so that
 * components (CodeTab, ChatInput) require minimal changes.
 */

import apiService from './apiService'
import { useAppStore } from '../stores/appStore'
import { mapExecutionServiceResponse } from '../utils/executionServiceMapper'

class ExecutionService {
    /**
     * Execute Python code on the backend.
     * Returns the same shape as the legacy executePython() contract.
     *
     * @param {string} code - Python code to execute
     * @returns {Promise<{success: boolean, stdout: string, stderr: string, error: string|null, result: any, resultType: string|null}>}
     */
    async executePython(code) {
        try {
            const appStore = useAppStore()
            const response = await apiService.executeCode(code, 60, appStore.activeWorkspaceId || null)
            return mapExecutionServiceResponse(response)
        } catch (err) {
            return {
                success: false,
                stdout: '',
                stderr: '',
                error: err?.response?.data?.detail || err.message || 'Execution failed',
                result: null,
                resultType: null,
                variables: { dataframes: {}, figures: {}, scalars: {} },
            }
        }
    }

}

const executionService = new ExecutionService()
export default executionService
