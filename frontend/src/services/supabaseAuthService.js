import { createClient } from '@supabase/supabase-js'
import { openExternalUrl } from './externalLinkService'

function readEnv(...names) {
  for (const name of names) {
    const value = String(import.meta.env[name] || '').trim()
    if (value) return value
  }
  return ''
}

const SUPABASE_URL = readEnv('VITE_SB_INQUIRA_CE_URL', 'SB_INQUIRA_CE_URL')
const SUPABASE_PUBLISHABLE_KEY = readEnv(
  'VITE_SB_INQUIRA_CE_PUBLISHABLE_KEY',
  'SB_INQUIRA_CE_PUBLISHABLE_KEY',
)
const SITE_URL = readEnv('VITE_SB_INQUIRA_CE_SITE_URL', 'SB_INQUIRA_CE_SITE_URL')
const MANAGE_ACCOUNT_URL = readEnv(
  'VITE_SB_INQUIRA_CE_MANAGE_ACCOUNT_URL',
  'SB_INQUIRA_CE_MANAGE_ACCOUNT_URL',
)
const FALLBACK_SITE_URL = 'https://seekerai.in'

const isBrowser = typeof window !== 'undefined'
const isTauriDesktop = isBrowser && !!window.__TAURI_INTERNALS__
const isConfigured = !!SUPABASE_URL && !!SUPABASE_PUBLISHABLE_KEY

let client = null
let callbackListenerPromise = null

function createSupabaseClient() {
  if (!isConfigured) return null
  return createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: !isTauriDesktop,
      flowType: 'pkce',
    },
  })
}

function getClient() {
  if (!client) {
    client = createSupabaseClient()
  }
  return client
}

function normalizeManageAccountUrl() {
  return MANAGE_ACCOUNT_URL || SITE_URL || FALLBACK_SITE_URL
}

async function ensureLoopbackListener() {
  if (!isTauriDesktop || callbackListenerPromise) return callbackListenerPromise

  callbackListenerPromise = Promise.all([
    import('@tauri-apps/api/event'),
  ]).then(async ([eventApi]) => {
    await eventApi.listen('auth:callback', async (event) => {
      const code = String(event?.payload?.code || '').trim()
      if (!code) return
      const sb = getClient()
      if (!sb) return
      const { error } = await sb.auth.exchangeCodeForSession(code)
      if (error) {
        console.error('❌ Failed to exchange Supabase auth code for session:', error)
      }
    })
  })

  return callbackListenerPromise
}

async function startLoopbackRedirect() {
  if (!isTauriDesktop) {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1'
    return `${origin.replace(/\/+$/, '')}/auth/callback`
  }

  await ensureLoopbackListener()
  const { invoke } = await import('@tauri-apps/api/core')
  const result = await invoke('auth_start_loopback_listener')
  return String(result?.redirect_url || '').trim()
}

async function signInWithProvider(provider) {
  const sb = getClient()
  if (!sb) {
    throw new Error(
      'Supabase auth is not configured. Set SB_INQUIRA_CE_URL and SB_INQUIRA_CE_PUBLISHABLE_KEY in the root .env file.',
    )
  }

  if (!isTauriDesktop) {
    const { error } = await sb.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin.replace(/\/+$/, '')}/auth/callback`,
      },
    })
    if (error) throw error
    return
  }

  const redirectTo = await startLoopbackRedirect()
  const { data, error } = await sb.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo,
      skipBrowserRedirect: true,
    },
  })
  if (error) throw error
  const authUrl = String(data?.url || '').trim()
  if (!authUrl) {
    throw new Error('Supabase did not return an OAuth redirect URL.')
  }
  await openExternalUrl(authUrl)
}

async function sendMagicLink(email) {
  const sb = getClient()
  if (!sb) {
    throw new Error(
      'Supabase auth is not configured. Set SB_INQUIRA_CE_URL and SB_INQUIRA_CE_PUBLISHABLE_KEY in the root .env file.',
    )
  }

  const emailAddress = String(email || '').trim()
  if (!emailAddress) {
    throw new Error('Email is required.')
  }

  const emailRedirectTo = await startLoopbackRedirect()
  const { error } = await sb.auth.signInWithOtp({
    email: emailAddress,
    options: {
      emailRedirectTo,
      shouldCreateUser: true,
    },
  })
  if (error) throw error
}

async function getSession() {
  const sb = getClient()
  if (!sb) return null
  const { data, error } = await sb.auth.getSession()
  if (error) throw error
  return data?.session || null
}

async function getAccessToken() {
  const session = await getSession()
  return String(session?.access_token || '').trim() || null
}

async function signOut() {
  const sb = getClient()
  if (!sb) return
  const { error } = await sb.auth.signOut()
  if (error) throw error
}

function onAuthStateChange(handler) {
  const sb = getClient()
  if (!sb) {
    return { data: { subscription: { unsubscribe() {} } } }
  }
  return sb.auth.onAuthStateChange(handler)
}

export const supabaseAuthService = {
  isConfigured,
  isTauriDesktop,
  getClient,
  getSession,
  getAccessToken,
  signInWithProvider,
  sendMagicLink,
  signOut,
  onAuthStateChange,
  getManageAccountUrl: normalizeManageAccountUrl,
}

export default supabaseAuthService
