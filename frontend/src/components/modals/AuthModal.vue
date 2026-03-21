<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto"
    aria-labelledby="modal-title"
    role="dialog"
    aria-modal="true"
  >
    <div
      class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
      @click="closeModal"
    ></div>

    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md"
        @click.stop
      >
        <div class="bg-white px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-center">
            <h3 class="text-lg font-semibold text-gray-900" id="modal-title">
              Sign In To Inquira
            </h3>
          </div>
        </div>

        <div class="bg-white px-6 py-6">
          <div class="mb-5">
            <p class="text-sm text-gray-600">
              Sign in once with your browser. Inquira will keep you signed in automatically on this desktop.
            </p>
          </div>

          <div v-if="displayMessage" :class="[
            'mb-4 p-4 rounded-md',
            isErrorMessage ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'
          ]">
            <div class="flex items-center">
              <CheckCircleIcon v-if="!isErrorMessage" class="h-5 w-5 text-green-500 mr-2" />
              <ExclamationTriangleIcon v-else class="h-5 w-5 text-red-500 mr-2" />
              <p :class="[
                'text-sm font-medium',
                isErrorMessage ? 'text-red-800' : 'text-green-800'
              ]">
                {{ displayMessage }}
              </p>
            </div>
          </div>

          <div class="space-y-3">
            <button
              @click="handleProviderSignIn('google')"
              :disabled="authStore.isLoading"
              class="w-full px-4 py-2.5 text-sm font-medium text-gray-800 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue with Google
            </button>
            <button
              @click="handleProviderSignIn('azure')"
              :disabled="authStore.isLoading"
              class="w-full px-4 py-2.5 text-sm font-medium text-gray-800 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue with Microsoft
            </button>
            <button
              @click="handleProviderSignIn('github')"
              :disabled="authStore.isLoading"
              class="w-full px-4 py-2.5 text-sm font-medium text-gray-800 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue with GitHub
            </button>
          </div>

          <div class="my-6 flex items-center gap-3">
            <div class="h-px flex-1 bg-gray-200"></div>
            <span class="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">or</span>
            <div class="h-px flex-1 bg-gray-200"></div>
          </div>

          <form @submit.prevent="handleMagicLink" class="space-y-3">
            <div>
              <label for="email" class="block text-sm font-medium text-gray-700 mb-2">
                Email Magic Link
              </label>
              <input
                id="email"
                type="email"
                v-model="email"
                required
                :disabled="authStore.isLoading"
                placeholder="you@company.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <button
              type="submit"
              :disabled="authStore.isLoading || !isEmailValid"
              class="w-full px-4 py-2.5 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send Magic Link
            </button>
          </form>

          <p class="mt-4 text-xs text-gray-500">
            Password changes and account management are handled in the browser.
          </p>
          <p class="mt-2 text-xs text-gray-500">
            By continuing, you agree to the
            <a
              href="/terms-and-conditions.html"
              @click.prevent="openTermsAndConditions"
              target="_blank"
              rel="noopener noreferrer"
              class="font-semibold text-blue-600 hover:text-blue-500"
            >
              Terms &amp; Conditions
            </a>.
          </p>
        </div>

        <div class="bg-gray-50 px-6 py-4">
          <button
            @click="closeModal"
            :disabled="authStore.isLoading"
            class="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { openExternalUrl } from '../../services/externalLinkService'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const authStore = useAuthStore()
const email = ref('')
const message = ref('')
const messageType = ref('')

const isEmailValid = computed(() => /\S+@\S+\.\S+/.test(String(email.value || '').trim()))

const displayMessage = computed(() => {
  return message.value || authStore.error
})

const isErrorMessage = computed(() => {
  return !!(authStore.error || (message.value && messageType.value === 'error'))
})

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

function showMessage(text, type) {
  message.value = text
  messageType.value = type
}

function openTermsAndConditions() {
  void openExternalUrl('https://github.com/adarsh9780/inquira-ce/blob/main/frontend/public/terms-and-conditions.html')
}

function closeModal() {
  if (authStore.isLoading) return
  emit('close')
}

async function handleProviderSignIn(provider) {
  clearMessage()
  const success = await authStore.signInWithProvider(provider)
  if (success) {
    showMessage('Browser opened. Finish sign-in there and Inquira will continue automatically.', 'success')
  }
}

async function handleMagicLink() {
  if (!isEmailValid.value) return
  clearMessage()
  const success = await authStore.sendMagicLink(email.value.trim())
  if (success) {
    showMessage('Magic link sent. Open it in your browser to finish sign-in.', 'success')
  }
}

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    clearMessage()
    authStore.clearError()
  }
})

watch(() => authStore.isAuthenticated, (isAuthenticated) => {
  if (isAuthenticated && props.isOpen) {
    emit('close')
  }
})
</script>
