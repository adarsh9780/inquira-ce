import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '../services/apiService'
import { settingsWebSocket } from '../services/websocketService'
import { supabaseAuthService } from '../services/supabaseAuthService'

export const useAuthStore = defineStore('auth', () => {
  const AUTH_PROBE_TIMEOUT_MS = 15000
  const AUTH_ACTION_TIMEOUT_MS = 45000

  const user = ref(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const error = ref('')
  const plan = ref('FREE')
  const pendingAuthAction = ref('')
  let authProbeRevision = 0
  let authSubscription = null

  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.user_id || '')
  const planLabel = computed(() => String(plan.value || 'FREE').toUpperCase())
  const manageAccountUrl = computed(() => supabaseAuthService.getManageAccountUrl())

  function sleep(ms) {
    return new Promise((resolve) => {
      setTimeout(resolve, ms)
    })
  }

  async function withTimeout(promise, timeoutMs, message) {
    let timer = null
    try {
      return await Promise.race([
        promise,
        new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error(message)), timeoutMs)
        }),
      ])
    } finally {
      if (timer) clearTimeout(timer)
    }
  }

  function clearLocalState() {
    user.value = null
    isAuthenticated.value = false
    plan.value = 'FREE'
  }

  async function hydrateUserFromBackend(accessToken = '') {
    const token = String(accessToken || '').trim()
    const requestConfig = token
      ? {
          timeout: AUTH_PROBE_TIMEOUT_MS,
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      : { timeout: AUTH_PROBE_TIMEOUT_MS }

    const profile = await withTimeout(
      apiService.v1GetCurrentUser(requestConfig),
      AUTH_PROBE_TIMEOUT_MS + 1000,
      'Authentication check timed out.',
    )
    if (profile?.user_id) {
      user.value = {
        user_id: profile.user_id,
        username: profile.username,
      }
      isAuthenticated.value = true
      plan.value = profile.plan || 'FREE'
      return true
    }
    clearLocalState()
    return false
  }

  async function hydrateUserFromBackendWithRetry(accessToken = '', maxAttempts = 3) {
    let lastError = null
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        return await hydrateUserFromBackend(accessToken)
      } catch (err) {
        lastError = err
        if (attempt >= maxAttempts) break
        await sleep(400 * attempt)
      }
    }
    throw lastError
  }

  function ensureAuthSubscription() {
    if (authSubscription || !supabaseAuthService.isConfigured) return
    const { data } = supabaseAuthService.onAuthStateChange(async (_event, session) => {
      authProbeRevision += 1
      const accessToken = String(session?.access_token || '').trim()
      if (!accessToken) {
        clearLocalState()
        error.value = ''
        pendingAuthAction.value = ''
        return
      }

      try {
        await hydrateUserFromBackendWithRetry(accessToken)
        error.value = ''
      } catch (err) {
        console.error('❌ Failed to hydrate Supabase session from backend:', err)
        clearLocalState()
        error.value = 'Authentication succeeded, but the local backend could not verify the session.'
      } finally {
        pendingAuthAction.value = ''
      }
    })
    authSubscription = data?.subscription || null
  }

  async function refreshPlan() {
    try {
      const profile = await withTimeout(
        apiService.v1GetCurrentUser({ timeout: AUTH_PROBE_TIMEOUT_MS }),
        AUTH_PROBE_TIMEOUT_MS + 1000,
        'Profile refresh timed out.',
      )
      if (profile?.plan) {
        plan.value = profile.plan
      }
    } catch (_err) {
      if (!plan.value) {
        plan.value = 'FREE'
      }
    }
  }

  async function checkAuth() {
    ensureAuthSubscription()
    const probeRevision = ++authProbeRevision
    error.value = ''

    try {
      const session = await withTimeout(
        supabaseAuthService.getSession(),
        AUTH_PROBE_TIMEOUT_MS,
        'Authentication check timed out.',
      )
      if (probeRevision !== authProbeRevision) return
      const accessToken = String(session?.access_token || '').trim()
      if (!accessToken) {
        clearLocalState()
        return
      }
      await hydrateUserFromBackend(accessToken)
    } catch (_err) {
      if (probeRevision !== authProbeRevision) return
      clearLocalState()
    }
  }

  async function signInWithProvider(provider) {
    if (isLoading.value) return false
    ensureAuthSubscription()

    authProbeRevision += 1
    isLoading.value = true
    error.value = ''
    pendingAuthAction.value = String(provider || '').trim()

    try {
      await withTimeout(
        supabaseAuthService.signInWithProvider(provider),
        AUTH_ACTION_TIMEOUT_MS,
        'Provider sign-in request timed out.',
      )
      return true
    } catch (err) {
      console.error('❌ Provider sign-in failed:', err)
      if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Sign-in timed out. Please try again.'
      } else {
        error.value = err?.message || 'Sign-in failed. Please try again.'
      }
      pendingAuthAction.value = ''
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function sendMagicLink(emailAddress) {
    if (isLoading.value) return false
    ensureAuthSubscription()

    authProbeRevision += 1
    isLoading.value = true
    error.value = ''
    pendingAuthAction.value = 'magic_link'

    try {
      await withTimeout(
        supabaseAuthService.sendMagicLink(emailAddress),
        AUTH_ACTION_TIMEOUT_MS,
        'Magic link request timed out.',
      )
      return true
    } catch (err) {
      console.error('❌ Magic link request failed:', err)
      if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Magic link request timed out. Please try again.'
      } else {
        error.value = err?.message || 'Failed to send magic link. Please try again.'
      }
      pendingAuthAction.value = ''
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    if (isLoading.value) return

    authProbeRevision += 1
    isLoading.value = true

    try {
      await withTimeout(
        supabaseAuthService.signOut(),
        AUTH_ACTION_TIMEOUT_MS,
        'Logout request timed out.',
      )
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }
      clearLocalState()
      error.value = ''
      pendingAuthAction.value = ''
    } catch (err) {
      console.error('❌ Logout failed:', err)
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }
      clearLocalState()
      pendingAuthAction.value = ''
    } finally {
      isLoading.value = false
    }
  }

  function clearError() {
    error.value = ''
  }

  ensureAuthSubscription()

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    plan,
    pendingAuthAction,
    username,
    userId,
    planLabel,
    manageAccountUrl,
    checkAuth,
    signInWithProvider,
    sendMagicLink,
    logout,
    refreshPlan,
    clearError,
  }
})
