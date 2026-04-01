<template>
  <div class="p-6">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
      <UserIcon class="w-6 h-6 mr-2 text-purple-600" />
      Account Settings
    </h2>

    <div v-if="message" :class="messageTypeClass" class="mb-4 p-3 rounded-md flex items-center">
      <CheckCircleIcon v-if="messageType === 'success'" class="w-5 h-5 mr-2 flex-shrink-0" />
      <ExclamationTriangleIcon v-else class="w-5 h-5 mr-2 flex-shrink-0" />
      <span class="text-sm">{{ message }}</span>
    </div>

    <div class="space-y-6">
      <div class="border rounded-lg p-4" style="border-color: var(--color-border);">
        <h3 class="text-lg font-medium mb-2" style="color: var(--color-text-main);">Signed In As</h3>
        <p class="text-sm mb-1" style="color: var(--color-text-main);">{{ authStore.username || 'Local User' }}</p>
        <p v-if="authStore.user?.email" class="text-xs mb-1" style="color: var(--color-text-muted);">{{ authStore.user.email }}</p>
        <p class="text-xs" style="color: var(--color-text-muted);">Plan: {{ authStore.planLabel }}</p>
        <p v-if="authStore.isGuest" class="text-xs mt-2" style="color: var(--color-text-muted);">
          You are currently using the free local mode. Sign in to connect your account without leaving the app.
        </p>
      </div>

      <div v-if="authStore.isGuest" class="border rounded-lg p-4" style="border-color: var(--color-border);">
        <h3 class="text-lg font-medium mb-3" style="color: var(--color-text-main);">Sign In / Sign Up</h3>
        <p class="text-sm mb-4" style="color: var(--color-text-muted);">
          Continue with Google to attach this app to an account. Free users can keep using the app either way.
        </p>
        <button
          @click="startGoogleSignIn"
          :disabled="isSigningIn || !authStore.canStartGoogleLogin"
          class="w-full px-4 py-2 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="isSigningIn" class="inline-flex items-center">
            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            Connecting to Google...
          </span>
          <span v-else>Continue with Google</span>
        </button>
        <p v-if="!authStore.canStartGoogleLogin" class="text-xs mt-3" style="color: var(--color-text-muted);">
          Google sign-in is not configured for this app yet.
        </p>
      </div>

      <div v-else class="border rounded-lg p-4" style="border-color: var(--color-border);">
        <h3 class="text-lg font-medium mb-3" style="color: var(--color-text-main);">Manage Account</h3>
        <p class="text-sm mb-4" style="color: var(--color-text-muted);">
          Billing, account recovery, and future account controls will open in the browser. The dedicated account app is still a placeholder.
        </p>
        <div class="space-y-3">
          <button
            @click="openManageAccount"
            :disabled="isOpeningManageAccount || !authStore.manageAccountUrl"
            class="w-full px-4 py-2 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isOpeningManageAccount" class="inline-flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Opening Browser...
            </span>
            <span v-else>Manage Account</span>
          </button>
          <button
            @click="signOut"
            :disabled="isSigningOut"
            class="w-full px-4 py-2 border rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            style="border-color: var(--color-border); color: var(--color-text-main);"
          >
            <span v-if="isSigningOut" class="inline-flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 mr-2" style="border-color: var(--color-text-muted);"></div>
              Signing Out...
            </span>
            <span v-else>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { openExternalUrl } from '../../services/externalLinkService'
import { toast } from '../../composables/useToast'
import {
  UserIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()

const isOpeningManageAccount = ref(false)
const isSigningIn = ref(false)
const isSigningOut = ref(false)
const message = ref('')
const messageType = ref('')

const messageTypeClass = computed(() => {
  return messageType.value === 'success'
    ? 'bg-green-50 border border-green-200 text-green-800'
    : 'bg-red-50 border border-red-200 text-red-800'
})

function showMessage(text, type) {
  message.value = text
  messageType.value = type
}

async function startGoogleSignIn() {
  isSigningIn.value = true
  try {
    const success = await authStore.signInWithProvider('google')
    if (!success) {
      throw new Error(authStore.error || 'Google sign-in did not complete.')
    }
    showMessage('Google sign-in completed successfully.', 'success')
    toast.success('Google Sign-In', 'Your account is now connected to this app.')
  } catch (signInError) {
    console.error('❌ Failed to sign in with Google:', signInError)
    showMessage(String(signInError?.message || 'Unable to sign in with Google.'), 'error')
  } finally {
    isSigningIn.value = false
  }
}

async function openManageAccount() {
  isOpeningManageAccount.value = true
  try {
    const opened = await openExternalUrl(authStore.manageAccountUrl)
    if (!opened) {
      throw new Error('Browser launch was blocked.')
    }
    showMessage('Account management opened in your browser.', 'success')
    toast.success('Manage Account', 'Browser opened for account management.')
  } catch (openError) {
    console.error('❌ Failed to open manage account URL:', openError)
    showMessage('Unable to open the browser for account management.', 'error')
  } finally {
    isOpeningManageAccount.value = false
  }
}

async function signOut() {
  isSigningOut.value = true
  try {
    const success = await authStore.logout()
    if (!success) {
      throw new Error(authStore.error || 'Sign-out did not complete.')
    }
    showMessage('You are now back in free local mode.', 'success')
    toast.success('Signed Out', 'You can keep using the free local mode.')
  } catch (logoutError) {
    console.error('❌ Failed to sign out:', logoutError)
    showMessage(String(logoutError?.message || 'Unable to sign out right now.'), 'error')
  } finally {
    isSigningOut.value = false
  }
}
</script>
