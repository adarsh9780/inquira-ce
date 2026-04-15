<template>
  <section class="h-full">
    <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">Account</h2>

    <div class="mb-5 flex items-center gap-3 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] p-4">
      <div class="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-sm font-medium text-[var(--color-accent)]">
        {{ initials }}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ displayName }}</p>
        <p v-if="displayEmail" class="truncate text-xs text-[var(--color-text-muted)]">{{ displayEmail }}</p>
        <p v-if="authStore.isGuest" class="mt-1 text-xs text-[var(--color-text-muted)]">
          Local User mode active. Add Google account sync session.
        </p>
        <p v-else-if="isGoogleLinked" class="mt-1 text-xs text-[var(--color-text-muted)]">
          Google account added already.
        </p>
        <p v-else class="mt-1 text-xs text-[var(--color-text-muted)]">
          Account connected.
        </p>
      </div>
    </div>

    <div class="mb-5 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] p-4">
      <label class="mb-1.5 block section-label">Theme</label>
      <HeaderDropdown
        :model-value="appStore.uiTheme"
        :options="themeOptions"
        placeholder="Select theme"
        aria-label="UI theme"
        max-width-class="w-full"
        @update:model-value="selectTheme"
      />
      <p class="mt-2 text-xs text-[var(--color-text-muted)]">
        Applies instantly across app surfaces. Midnight keeps the brand accent while reducing glare.
      </p>
    </div>

    <div class="space-y-4">
      <template v-if="authStore.isGuest">
        <button
          type="button"
          class="flex w-full items-center justify-center gap-3 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)] py-2.5 text-sm font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-soft)] disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isSigningIn || !authStore.canStartGoogleLogin"
          @click="startGoogleSignIn"
        >
          <svg class="h-[18px] w-[18px]" viewBox="0 0 18 18" aria-hidden="true">
            <path fill="#4285F4" d="M17.64 9.2045c0-.6382-.0573-1.2518-.1636-1.8409H9v3.4818h4.8436c-.2087 1.125-.8427 2.0782-1.7986 2.715v2.2582h2.9086c1.7018-1.5668 2.6864-3.8741 2.6864-6.6141z" />
            <path fill="#34A853" d="M9 18c2.43 0 4.4673-.8059 5.9564-2.1818l-2.9086-2.2582c-.8059.54-1.8368.8591-3.0478.8591-2.3441 0-4.3282-1.5832-5.0364-3.7105H.9573v2.3318C2.4382 15.9805 5.4818 18 9 18z" />
            <path fill="#FBBC05" d="M3.9636 10.7086c-.18-.54-.2836-1.1168-.2836-1.7086s.1036-1.1686.2836-1.7086V4.9596H.9573C.3477 6.1732 0 7.545 0 9s.3477 2.8268.9573 4.0405l3.0063-2.3319z" />
            <path fill="#EA4335" d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.3459l2.5814-2.5814C13.4632.8918 11.4273 0 9 0 5.4818 0 2.4382 2.0195.9573 4.9595l3.0063 2.3319C4.6718 5.1627 6.6559 3.5795 9 3.5795z" />
          </svg>
          <span v-if="isSigningIn">Connecting Google...</span>
          <span v-else>Sign in with Google</span>
        </button>
        <p v-if="!authStore.canStartGoogleLogin" class="text-xs text-[var(--color-text-muted)]">
          Google sign-in not configured yet.
        </p>
      </template>

      <template v-else>
        <div class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-2">
          <p class="text-xs text-[var(--color-text-main)]">Google account linked current session.</p>
          <p class="mt-1 text-xs text-[var(--color-text-muted)]">Sign out from Google converts account back Local User mode.</p>
        </div>
        <button
          type="button"
          class="flex w-full items-center justify-center gap-3 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)] py-2.5 text-sm font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-soft)] disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isSigningOut"
          @click="signOutGoogle"
        >
          <span v-if="isSigningOut">Signing out from Google...</span>
          <span v-else>Sign out from Google</span>
        </button>
      </template>
    </div>

    <div class="mt-5 flex justify-end border-t border-[var(--color-border)] pt-4">
      <div class="flex items-center gap-2">
        <button type="button" class="btn-secondary px-4 py-2 text-sm">
          Cancel
        </button>
        <button type="button" class="btn-primary px-4 py-2 text-sm">
          Save preferences
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import HeaderDropdown from '../../ui/HeaderDropdown.vue'
import { useAppStore } from '../../../stores/appStore'
import { useAuthStore } from '../../../stores/authStore'
import { toast } from '../../../composables/useToast'

const appStore = useAppStore()
const authStore = useAuthStore()

const isSigningIn = computed(() => authStore.pendingAuthAction === 'google' && authStore.isLoading)
const isSigningOut = ref(false)
const isGoogleLinked = computed(() => {
  if (authStore.isGuest) return false
  return String(authStore.user?.auth_provider || '').trim().toLowerCase() === 'google'
})
const displayName = computed(() => String(authStore.username || 'Local User').trim() || 'Local User')
const displayEmail = computed(() => String(authStore.user?.email || '').trim())
const themeOptions = computed(() => {
  const options = Array.isArray(appStore.availableThemes) ? appStore.availableThemes : []
  return options.map((theme) => ({
    value: theme.id,
    label: theme.label,
  }))
})

const initials = computed(() => {
  const parts = String(displayName.value || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return 'U'
  return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join('')
})

async function startGoogleSignIn() {
  if (isSigningIn.value || !authStore.canStartGoogleLogin) return
  try {
    const success = await authStore.signInWithProvider('google')
    if (!success) {
      throw new Error(authStore.error || 'Google sign-in did not complete.')
    }
    toast.success('Google account added', 'Account connected successfully.')
  } catch (error) {
    console.error('Failed to sign in with Google:', error)
    toast.error('Google sign-in failed', String(error?.message || 'Could not complete Google sign-in.'))
  }
}

async function signOutGoogle() {
  if (isSigningOut.value) return
  isSigningOut.value = true
  try {
    const success = await authStore.logout()
    if (!success) {
      throw new Error(authStore.error || 'Sign-out did not complete.')
    }
    toast.success('Signed out from Google', 'Account switched back Local User mode.')
  } catch (error) {
    console.error('Failed to sign out from Google:', error)
    toast.error('Sign-out failed', String(error?.message || 'Could not sign out from Google.'))
  } finally {
    isSigningOut.value = false
  }
}

function selectTheme(themeId) {
  appStore.setUiTheme(themeId)
}
</script>
