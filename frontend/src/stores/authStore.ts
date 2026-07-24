import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export interface LocalUserProfile {
  user_id: string
  username: string
  email: string
  auth_provider: 'local'
  is_authenticated: boolean
  is_guest: boolean
  plan: string
  manage_account_url: string
}

const DEFAULT_LOCAL_USER = Object.freeze({
  user_id: 'local-user',
  username: 'Local User',
  email: '',
  auth_provider: 'local',
  is_authenticated: false,
  is_guest: true,
})

function localProfile(plan = 'FREE'): LocalUserProfile {
  return {
    ...DEFAULT_LOCAL_USER,
    plan,
    manage_account_url: '',
  }
}

function resolveUsername(profile: Partial<LocalUserProfile>): string {
  const candidates = [profile?.username, profile?.email, DEFAULT_LOCAL_USER.username]
  for (const candidate of candidates) {
    const value = String(candidate || '').trim()
    if (value) return value
  }
  return DEFAULT_LOCAL_USER.username
}

function normalizeLocalProfile(profile: Partial<LocalUserProfile> = {}): LocalUserProfile {
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
  const user = ref<LocalUserProfile>(localProfile())
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

  function clearError(): void {
    error.value = ''
  }

  function applyProfile(profile: Partial<LocalUserProfile>): void {
    const normalized = normalizeLocalProfile(profile)
    user.value = normalized
    plan.value = normalized.plan
    // CE is local-first: the shell should enter without requiring account auth.
    isAuthenticated.value = true
  }

  function setLocalState(): void {
    applyProfile(localProfile())
  }

  async function initialize(): Promise<boolean> {
    isLoading.value = true
    clearError()
    try {
      setLocalState()
      return true
    } finally {
      initialSessionResolved.value = true
      isLoading.value = false
    }
  }

  async function checkAuth(): Promise<boolean> {
    clearError()
    setLocalState()
    return true
  }

  async function sendMagicLink(): Promise<boolean> {
    error.value = 'Sign-in is not available in Inquira CE.'
    return false
  }

  async function logout(): Promise<boolean> {
    clearError()
    isLoading.value = true
    try {
      setLocalState()
      authFlowStage.value = 'local'
      authFlowMessage.value = 'Local workspace mode is active.'
      return true
    } finally {
      isLoading.value = false
    }
  }

  async function refreshPlan(): Promise<boolean> {
    return checkAuth()
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
