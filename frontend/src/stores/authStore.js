import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { openExternalUrl } from '../services/externalLinkService'
import { getAuthConfig } from '../services/authConfigService'
import { getSupabaseClient } from '../services/supabaseAuthService'
import { apiService } from '../services/apiService'

const DEFAULT_GUEST_USER = Object.freeze({
  user_id: 'local-user',
  username: 'Local User',
  email: '',
  auth_provider: 'local',
  is_authenticated: false,
  is_guest: true,
})

function guestProfile(plan = 'FREE') {
  return {
    ...DEFAULT_GUEST_USER,
    plan,
    manage_account_url: '',
  }
}

function normalizeManageAccountUrl(config, profile) {
  if (!profile?.is_authenticated || profile?.is_guest) return ''
  return String(profile?.manage_account_url || config?.manage_account_url || '').trim()
}

function resolveUsername(profile) {
  const candidates = [profile?.username, profile?.email, DEFAULT_GUEST_USER.username]
  for (const candidate of candidates) {
    const value = String(candidate || '').trim()
    if (value) return value
  }
  return DEFAULT_GUEST_USER.username
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref({ ...DEFAULT_GUEST_USER })
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
    auth_provider: 'supabase',
    supabase_url: '',
    publishable_key: '',
    site_url: '',
    manage_account_url: '',
  })

  let supabaseClient = null
  let authSubscription = null

  const username = computed(() => resolveUsername(user.value))
  const userId = computed(() => String(user.value?.user_id || DEFAULT_GUEST_USER.user_id).trim())
  const planLabel = computed(() => String(plan.value || 'FREE').trim().toUpperCase() || 'FREE')
  const isGuest = computed(() => Boolean(user.value?.is_guest !== false))
  const isSignedIn = computed(() => Boolean(user.value?.is_authenticated) && !isGuest.value)
  const canStartGoogleLogin = computed(() => Boolean(authConfig.value?.configured))
  const manageAccountUrl = computed(() => normalizeManageAccountUrl(authConfig.value, user.value))

  function clearError() {
    error.value = ''
  }

  function applyProfile(profile) {
    const normalizedPlan = String(profile?.plan || 'FREE').trim().toUpperCase() || 'FREE'
    user.value = {
      user_id: String(profile?.user_id || DEFAULT_GUEST_USER.user_id).trim() || DEFAULT_GUEST_USER.user_id,
      username: resolveUsername(profile),
      email: String(profile?.email || '').trim(),
      auth_provider: String(profile?.auth_provider || 'local').trim() || 'local',
      is_authenticated: Boolean(profile?.is_authenticated),
      is_guest: Boolean(profile?.is_guest),
      manage_account_url: normalizeManageAccountUrl(authConfig.value, profile),
    }
    plan.value = normalizedPlan
    // Guest users must still enter the shell. The shell remains available,
    // but the account tab can later upgrade them into a signed-in session.
    isAuthenticated.value = true
  }

  function setGuestState() {
    apiService.setAuthToken('')
    applyProfile(guestProfile())
  }

  async function ensureAuthClient() {
    authConfig.value = await getAuthConfig()
    supabaseClient = await getSupabaseClient(authConfig.value)
    return supabaseClient
  }

  async function bindAuthStateListener() {
    if (!supabaseClient || authSubscription) return
    const { data } = supabaseClient.auth.onAuthStateChange(async (_event, session) => {
      const nextToken = String(session?.access_token || '').trim()
      apiService.setAuthToken(nextToken)
      if (!nextToken) {
        setGuestState()
        return
      }
      await checkAuth({ preserveSession: true })
    })
    authSubscription = data?.subscription || null
  }

  async function exchangeDesktopAuthCode(provider) {
    const [{ invoke }, { listen }] = await Promise.all([
      import('@tauri-apps/api/core'),
      import('@tauri-apps/api/event'),
    ])

    const callbackPromise = new Promise((resolve, reject) => {
      let timeoutId = null
      let unlistenRef = null
      const settle = async (fn, value) => {
        if (timeoutId) clearTimeout(timeoutId)
        if (typeof unlistenRef === 'function') {
          try {
            await unlistenRef()
          } catch (_error) {
            // Ignore listener cleanup errors.
          }
        }
        fn(value)
      }

      listen('auth:callback', async (event) => {
        await settle(resolve, event?.payload || {})
      })
        .then((unlisten) => {
          unlistenRef = unlisten
          timeoutId = window.setTimeout(() => {
            void settle(reject, new Error('Google sign-in timed out.'))
          }, 120000)
        })
        .catch((listenerError) => {
          void settle(reject, listenerError)
        })
    })

    const loopback = await invoke('auth_start_loopback_listener')
    const redirectTo = String(loopback?.redirect_url || '').trim()
    if (!redirectTo) {
      throw new Error('Desktop sign-in callback did not provide a redirect URL.')
    }

    const { data, error: signInError } = await supabaseClient.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo,
        skipBrowserRedirect: true,
        queryParams: {
          prompt: 'select_account',
        },
      },
    })
    if (signInError) throw signInError
    if (!data?.url) {
      throw new Error('Google sign-in URL was not generated.')
    }

    authFlowStage.value = 'browser'
    authFlowMessage.value = 'Waiting for Google sign-in to finish in your browser.'
    const opened = await openExternalUrl(data.url)
    if (!opened) {
      throw new Error('Unable to open the browser for Google sign-in.')
    }

    const payload = await callbackPromise
    if (payload?.error) {
      throw new Error(String(payload.error_description || payload.error || 'Google sign-in failed.'))
    }
    const code = String(payload?.code || '').trim()
    if (!code) {
      throw new Error('Google sign-in did not return an authorization code.')
    }

    authFlowStage.value = 'exchange'
    authFlowMessage.value = 'Finalizing your Google sign-in session.'
    const { error: exchangeError, data: exchangeData } = await supabaseClient.auth.exchangeCodeForSession(code)
    if (exchangeError) throw exchangeError
    const accessToken = String(exchangeData?.session?.access_token || '').trim()
    apiService.setAuthToken(accessToken)
  }

  async function initialize() {
    isLoading.value = true
    clearError()
    try {
      await ensureAuthClient()
      await bindAuthStateListener()

      if (supabaseClient) {
        const { data } = await supabaseClient.auth.getSession()
        const accessToken = String(data?.session?.access_token || '').trim()
        apiService.setAuthToken(accessToken)
      } else {
        apiService.setAuthToken('')
      }

      await checkAuth({ preserveSession: true })
      return true
    } catch (initError) {
      console.warn('Auth initialization fell back to guest mode:', initError)
      setGuestState()
      error.value = ''
      return false
    } finally {
      initialSessionResolved.value = true
      isLoading.value = false
    }
  }

  async function checkAuth({ preserveSession = false } = {}) {
    try {
      const profile = await apiService.verifyAuth()
      applyProfile(profile)
      clearError()
      return true
    } catch (authError) {
      if (!preserveSession || !isAuthenticated.value || isGuest.value) {
        setGuestState()
      }
      const status = Number(authError?.status || authError?.response?.status || 0)
      if (status === 401 || status === 403) {
        error.value = 'Your sign-in session expired. You are back in free local mode.'
        setGuestState()
        return false
      }
      if (!preserveSession) {
        error.value = String(authError?.message || 'Unable to verify your account session.')
      }
      return false
    }
  }

  async function signInWithProvider(provider = 'google') {
    clearError()
    if (String(provider || '').trim().toLowerCase() !== 'google') {
      error.value = 'Only Google sign-in is supported right now.'
      return false
    }

    isLoading.value = true
    pendingAuthAction.value = 'google'
    authFlowStage.value = 'start'
    authFlowMessage.value = 'Preparing Google sign-in.'

    try {
      await ensureAuthClient()
      await bindAuthStateListener()
      if (!supabaseClient || !authConfig.value?.configured) {
        throw new Error('Google sign-in is not configured yet for this app.')
      }

      if (typeof window !== 'undefined' && window.__TAURI_INTERNALS__) {
        await exchangeDesktopAuthCode('google')
      } else {
        const { error: signInError } = await supabaseClient.auth.signInWithOAuth({
          provider: 'google',
          options: {
            redirectTo: authConfig.value.site_url || window.location.origin,
          },
        })
        if (signInError) throw signInError
        return true
      }

      await checkAuth({ preserveSession: false })
      return isSignedIn.value
    } catch (signInError) {
      console.error('Google sign-in failed:', signInError)
      error.value = String(signInError?.message || 'Google sign-in failed.')
      authFlowStage.value = 'error'
      authFlowMessage.value = error.value
      return false
    } finally {
      pendingAuthAction.value = ''
      isLoading.value = false
    }
  }

  async function sendMagicLink() {
    error.value = 'Magic-link sign-in is not supported in CE.'
    return false
  }

  async function logout() {
    clearError()
    isLoading.value = true
    try {
      if (supabaseClient) {
        const { error: signOutError } = await supabaseClient.auth.signOut()
        if (signOutError) throw signOutError
      }
      apiService.setAuthToken('')
      await apiService.v1Logout().catch(() => ({ message: 'Session cleared locally.' }))
      setGuestState()
      authFlowStage.value = 'signed-out'
      authFlowMessage.value = 'You are back in free local mode.'
      return true
    } catch (logoutError) {
      console.error('Logout failed:', logoutError)
      error.value = String(logoutError?.message || 'Unable to sign out right now.')
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
    canStartGoogleLogin,
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
