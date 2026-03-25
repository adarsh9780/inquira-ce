import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * CE auth store — auto-authenticates as a local user.
 * No signup, no login, no Supabase.
 * Exports the same interface as the EE auth store so components work unchanged.
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const error = ref('')
  const plan = ref('FREE')
  const pendingAuthAction = ref('')
  const authFlowStage = ref('')
  const authFlowMessage = ref('')
  const initialSessionResolved = ref(false)

  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.user_id || '')
  const planLabel = computed(() => 'FREE')
  const manageAccountUrl = computed(() => '')

  function clearError() {
    error.value = ''
  }

  async function initialize() {
    user.value = { user_id: 'local-user', username: 'Local User' }
    isAuthenticated.value = true
    plan.value = 'FREE'
    initialSessionResolved.value = true
    return true
  }

  async function checkAuth() {
    return true
  }

  async function signInWithProvider() {
    return false
  }

  async function sendMagicLink() {
    return false
  }

  async function logout() {
    // No-op in CE — there's nothing to log out of.
  }

  async function refreshPlan() {
    plan.value = 'FREE'
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    plan,
    pendingAuthAction,
    authFlowStage,
    authFlowMessage,
    initialSessionResolved,
    username,
    userId,
    planLabel,
    manageAccountUrl,
    initialize,
    checkAuth,
    signInWithProvider,
    sendMagicLink,
    logout,
    refreshPlan,
    clearError,
  }
})
