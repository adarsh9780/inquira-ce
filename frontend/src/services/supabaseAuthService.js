import { createClient } from '@supabase/supabase-js'

let clientPromise = null

function storageKey() {
  return 'inquira-ce-auth'
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
          storageKey: storageKey(),
        },
      }),
    )
  }
  return clientPromise
}
