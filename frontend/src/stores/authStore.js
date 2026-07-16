import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiService } from '../services/apiService'

const DEFAULT_LOCAL_USER = Object.freeze({
  user_id: 'local-user',
  username: 'Local User',
  email: '',
  auth_provider: 'local',
  is_authenticated: false,
  is_guest: true,
})

function localProfile(plan = 'FREE') {
  return {
    ...DEFAULT_LOCAL_USER,
    plan,
    manage_account_url: '',
  }
}

function resolveUsername(profile) {
  const candidates = [profile?.username, profile?.email, DEFAULT_LOCAL_USER.username]
  for (const candidate of candidates) {
    const value = String(candidate || '').trim()
    if (value) return value
  }
  return DEFAULT_LOCAL_USER.username
}

function normalizeLocalProfile(profile = {}) {
  const normalizedPlan = String(profile?.plan || 'FREE').trim().toUpperCase() || 'FREE'
  return {
    user_id: String(profile?.user_id || DEFAULT_LOCAL_USER.user_id).trim() || DEFAULT_LOCAL_USER.user_id,
    username: resolveUsername(profile),
    email: String(profile?.email || '').trim(),
    auth_provider: 'local',
    is_authenticated: false,
    is_guest: true,
    manage_account_url: '',
    plan: normalizedPlan,
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref({ ...DEFAULT_LOCAL_USER })
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const error = ref('')
  const plan = ref('FREE')
  const pendingAuthAction = ref('')
  const authFlowStage = ref('')
  const authFlowMessage = ref('')
  const initialSessionResolved = ref(false)
  const authConfig = ref({
    configured: false,
    auth_provider: 'local',
    site_url: '',
    manage_account_url: '',
  })

  const username = computed(() => resolveUsername(user.value))
  const userId = computed(() => String(user.value?.user_id || DEFAULT_LOCAL_USER.user_id).trim())
  const planLabel = computed(() => String(plan.value || 'FREE').trim().toUpperCase() || 'FREE')
  const isGuest = computed(() => true)
  const isSignedIn = computed(() => false)
  const manageAccountUrl = computed(() => '')

  function clearError() {
    error.value = ''
  }

  function applyProfile(profile) {
    const normalized = normalizeLocalProfile(profile)
    user.value = normalized
    plan.value = normalized.plan
    // CE is local-first: the shell should enter without requiring account auth.
    isAuthenticated.value = true
  }

  function setLocalState() {
    apiService.setAuthToken('')
    applyProfile(localProfile())
  }

  async function initialize() {
    isLoading.value = true
    clearError()
    try {
      apiService.setAuthToken('')
      await checkAuth({ preserveSession: true })
      return true
    } catch (_initError) {
      setLocalState()
      return false
    } finally {
      initialSessionResolved.value = true
      isLoading.value = false
    }
  }

  async function checkAuth({ preserveSession = false } = {}) {
    try {
      apiService.setAuthToken('')
      const profile = await apiService.verifyAuth()
      applyProfile(profile)
      clearError()
      return true
    } catch (authError) {
      setLocalState()
      if (!preserveSession) {
        error.value = String(authError?.message || 'Unable to verify the local session.')
      }
      return false
    }
  }

  async function sendMagicLink() {
    error.value = 'Sign-in is not available in Inquira CE.'
    return false
  }

  async function logout() {
    clearError()
    isLoading.value = true
    try {
      apiService.setAuthToken('')
      await apiService.v1Logout().catch(() => ({ message: 'Local session cleared.' }))
      setLocalState()
      authFlowStage.value = 'local'
      authFlowMessage.value = 'Local workspace mode is active.'
      return true
    } catch (logoutError) {
      error.value = String(logoutError?.message || 'Unable to clear the local session right now.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function refreshPlan() {
    return checkAuth({ preserveSession: true })
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
    authConfig,
    username,
    userId,
    planLabel,
    isGuest,
    isSignedIn,
    manageAccountUrl,
    initialize,
    checkAuth,
    sendMagicLink,
    logout,
    refreshPlan,
    clearError,
  }
})
