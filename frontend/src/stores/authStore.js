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
  const authFlowStage = ref('')
  const authFlowMessage = ref('')
  let authProbeRevision = 0
  let authSubscription = null
  let authProgressListenerBound = false

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

  function setAuthFlow(stage, message = '') {
    authFlowStage.value = String(stage || '').trim()
    authFlowMessage.value = String(message || '').trim()
  }

  function clearAuthFlow() {
    authFlowStage.value = ''
    authFlowMessage.value = ''
  }

  async function hydrateUserFromBackend(accessToken = '') {
    await apiService.waitForBackendReady(AUTH_PROBE_TIMEOUT_MS)
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
        clearAuthFlow()
        return
      }

      try {
        setAuthFlow('verifying_session', 'Browser sign-in finished. Verifying your session with Inquira...')
        await hydrateUserFromBackendWithRetry(accessToken)
        error.value = ''
        setAuthFlow('loading_account', 'Session verified. Loading your account...')
      } catch (err) {
        console.error('❌ Failed to hydrate Supabase session from backend:', err)
        clearLocalState()
        error.value = 'Authentication succeeded, but the local backend could not verify the session.'
        setAuthFlow('failed', 'Browser sign-in finished, but Inquira could not verify your session yet.')
      } finally {
        pendingAuthAction.value = ''
      }
    })
    authSubscription = data?.subscription || null
  }

  function ensureDesktopAuthProgressListener() {
    if (authProgressListenerBound || typeof window === 'undefined') return
    window.addEventListener('inquira:auth-progress', (event) => {
      const stage = String(event?.detail?.stage || '').trim()
      const message = String(event?.detail?.message || '').trim()
      if (stage === 'browser_complete') {
        setAuthFlow('browser_complete', 'Browser sign-in finished. Completing sign-in in the app...')
        return
      }
      if (stage === 'exchanging_code') {
        setAuthFlow('exchanging_code', 'Received browser callback. Exchanging your sign-in code...')
        return
      }
      if (stage === 'session_ready') {
        setAuthFlow('session_ready', 'Sign-in code accepted. Waiting for Inquira backend...')
        return
      }
      if (stage === 'exchange_failed') {
        setAuthFlow('failed', message || 'Inquira could not finish the sign-in exchange.')
      }
    })
    authProgressListenerBound = true
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
    ensureDesktopAuthProgressListener()
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
    ensureDesktopAuthProgressListener()

    authProbeRevision += 1
    isLoading.value = true
    error.value = ''
    pendingAuthAction.value = String(provider || '').trim()
    setAuthFlow('browser_opening', 'Opening your browser for sign-in...')

    try {
      await withTimeout(
        supabaseAuthService.signInWithProvider(provider),
        AUTH_ACTION_TIMEOUT_MS,
        'Provider sign-in request timed out.',
      )
      setAuthFlow('browser_wait', 'Browser opened. Finish sign-in there and return to Inquira.')
      return true
    } catch (err) {
      console.error('❌ Provider sign-in failed:', err)
      if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Sign-in timed out. Please try again.'
      } else {
        error.value = err?.message || 'Sign-in failed. Please try again.'
      }
      pendingAuthAction.value = ''
      setAuthFlow('failed', error.value)
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
    setAuthFlow('magic_link_sending', 'Sending your magic link...')

    try {
      await withTimeout(
        supabaseAuthService.sendMagicLink(emailAddress),
        AUTH_ACTION_TIMEOUT_MS,
        'Magic link request timed out.',
      )
      setAuthFlow('magic_link_sent', 'Magic link sent. Open it in your browser to finish sign-in.')
      return true
    } catch (err) {
      console.error('❌ Magic link request failed:', err)
      if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Magic link request timed out. Please try again.'
      } else {
        error.value = err?.message || 'Failed to send magic link. Please try again.'
      }
      pendingAuthAction.value = ''
      setAuthFlow('failed', error.value)
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
      clearAuthFlow()
    } catch (err) {
      console.error('❌ Logout failed:', err)
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }
      clearLocalState()
      pendingAuthAction.value = ''
      clearAuthFlow()
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
    authFlowStage,
    authFlowMessage,
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
