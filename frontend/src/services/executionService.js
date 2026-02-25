/**
 * executionService.js — Server-Side Code Execution
 *
 * Drop-in replacement for the legacy in-browser Python execution service.
 * Instead of running Python in the browser,
 * this service sends code to the backend for execution and returns results.
 *
 * The API contract is intentionally kept stable so that
 * components (CodeTab, ChatInput, NotebookCell) require minimal changes.
 */

import apiService from './apiService'
import { useAppStore } from '../stores/appStore'

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
            return {
                success: response.success !== false,
                stdout: response.stdout || '',
                stderr: response.stderr || '',
                error: response.error || null,
                result: response.result || null,
                resultType: response.result_type || null,
            }
        } catch (err) {
            return {
                success: false,
                stdout: '',
                stderr: '',
                error: err?.response?.data?.detail || err.message || 'Execution failed',
                result: null,
                resultType: null,
            }
        }
    }

    /**
     * No-op: initialization is no longer needed.
     * Kept for API compatibility if any component calls it.
     */
    async initialize(_opts) {
        console.debug('[ExecutionService] Server-side execution ready (no initialization needed)')
    }

    /**
     * No-op: State restoration via accumulated code blocks is no longer needed.
     * The backend manages its own session state.
     */
    async restoreState(_codeBlocks) {
        console.debug('[ExecutionService] Server manages state (no restoration needed)')
    }
}

const executionService = new ExecutionService()
export default executionService
