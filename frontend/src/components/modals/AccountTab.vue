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
        <p class="text-sm mb-1" style="color: var(--color-text-main);">{{ authStore.username || 'Unknown account' }}</p>
        <p class="text-xs" style="color: var(--color-text-muted);">Plan: {{ authStore.planLabel }}</p>
      </div>

      <div class="border rounded-lg p-4" style="border-color: var(--color-border);">
        <h3 class="text-lg font-medium mb-3" style="color: var(--color-text-main);">Manage Account</h3>
        <p class="text-sm mb-4" style="color: var(--color-text-muted);">
          Password changes, account recovery, and any future account controls are handled in the browser.
        </p>
        <button
          @click="openManageAccount"
          :disabled="isOpeningManageAccount"
          class="w-full px-4 py-2 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="isOpeningManageAccount" class="inline-flex items-center">
            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            Opening Browser...
          </span>
          <span v-else>Manage Account</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { openExternalUrl } from '../../services/externalLinkService'
import { toast } from '../../composables/useToast'
import {
  UserIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()

const isOpeningManageAccount = ref(false)
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

async function openManageAccount() {
  isOpeningManageAccount.value = true
  try {
    const opened = await openExternalUrl(authStore.manageAccountUrl)
    if (!opened) {
      throw new Error('Browser launch was blocked.')
    }
    showMessage('Account management opened in your browser.', 'success')
    toast.success('Manage Account', 'Browser opened for account management.')
  } catch (error) {
    console.error('❌ Failed to open manage account URL:', error)
    showMessage('Unable to open the browser for account management.', 'error')
  } finally {
    isOpeningManageAccount.value = false
  }
}
</script>
