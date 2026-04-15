import { createClient } from '@supabase/supabase-js'

let clientPromise = null

function storageKey() {
  return 'inquira-ce-auth'
}

function isTauriDesktop() {
  return typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__)
}

export async function getSupabaseClient(config) {
  if (!config?.configured || !config?.supabase_url || !config?.publishable_key) {
    return null
  }
  if (!clientPromise) {
    clientPromise = Promise.resolve(
      createClient(config.supabase_url, config.publishable_key, {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: false,
          flowType: isTauriDesktop() ? 'pkce' : 'implicit',
          storageKey: storageKey(),
        },
      }),
    )
  }
  return clientPromise
}
