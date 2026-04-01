import { v1Api } from './contracts/v1Api'

function readEnvValue(name) {
  return String(import.meta.env?.[name] || '').trim()
}

function normalizeUrl(value) {
  return String(value || '').trim()
}

function envConfig() {
  const supabaseUrl = normalizeUrl(readEnvValue('VITE_SB_INQUIRA_CE_URL') || readEnvValue('SB_INQUIRA_CE_URL'))
  const publishableKey = normalizeUrl(
    readEnvValue('VITE_SB_INQUIRA_CE_PUBLISHABLE_KEY') || readEnvValue('SB_INQUIRA_CE_PUBLISHABLE_KEY'),
  )
  const siteUrl = normalizeUrl(readEnvValue('VITE_SB_INQUIRA_CE_SITE_URL'))
  const manageAccountUrl = normalizeUrl(
    readEnvValue('VITE_SB_INQUIRA_CE_MANAGE_ACCOUNT_URL') || siteUrl,
  )
  return {
    configured: Boolean(supabaseUrl && publishableKey),
    auth_provider: 'supabase',
    supabase_url: supabaseUrl,
    publishable_key: publishableKey,
    site_url: siteUrl,
    manage_account_url: manageAccountUrl,
  }
}

export async function getAuthConfig() {
  try {
    const config = await v1Api.auth.config()
    if (config && typeof config === 'object') {
      return {
        configured: Boolean(config.configured),
        auth_provider: String(config.auth_provider || 'supabase'),
        supabase_url: normalizeUrl(config.supabase_url),
        publishable_key: normalizeUrl(config.publishable_key),
        site_url: normalizeUrl(config.site_url),
        manage_account_url: normalizeUrl(config.manage_account_url),
      }
    }
  } catch (error) {
    console.warn('Falling back to env-based auth config:', error)
  }

  return envConfig()
}
