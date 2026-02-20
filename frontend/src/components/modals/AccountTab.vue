<template>
  <div class="p-6">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
      <UserIcon class="w-6 h-6 mr-2 text-purple-600" />
      Account Settings
    </h2>

    <!-- Success/Error Messages -->
    <div v-if="message" :class="messageTypeClass" class="mb-4 p-3 rounded-md flex items-center">
      <CheckCircleIcon v-if="messageType === 'success'" class="w-5 h-5 mr-2 flex-shrink-0" />
      <ExclamationTriangleIcon v-else class="w-5 h-5 mr-2 flex-shrink-0" />
      <span class="text-sm">{{ message }}</span>
    </div>

    <div class="space-y-6">
      <!-- Change Password Section -->
      <div class="border border-gray-200 rounded-lg p-4">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Change Password</h3>

        <div class="space-y-4">
          <!-- Current Password -->
          <div>
            <label for="current-password" class="block text-sm font-medium text-gray-700 mb-2">
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              v-model="currentPassword"
              :disabled="isChangingPassword"
              placeholder="Enter your current password"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <!-- New Password -->
          <div>
            <label for="new-password" class="block text-sm font-medium text-gray-700 mb-2">
              New Password
            </label>
            <input
              id="new-password"
              type="password"
              v-model="newPassword"
              :disabled="isChangingPassword"
              placeholder="Enter your new password"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <p class="mt-1 text-xs text-gray-500">
              Password must be at least 8 characters long
            </p>
          </div>

          <!-- Confirm New Password -->
          <div>
            <label for="confirm-password" class="block text-sm font-medium text-gray-700 mb-2">
              Confirm New Password
            </label>
            <input
              id="confirm-password"
              type="password"
              v-model="confirmPassword"
              :disabled="isChangingPassword"
              placeholder="Confirm your new password"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <!-- Change Password Button -->
          <button
            @click="changePassword"
            :disabled="!canChangePassword || isChangingPassword"
            class="w-full px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="isChangingPassword" class="inline-flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Changing Password...
            </span>
            <span v-else>Change Password</span>
          </button>
        </div>
      </div>

      <!-- Delete Account Section -->
      <div class="border border-red-200 rounded-lg p-4 bg-red-50">
        <h3 class="text-lg font-medium text-red-900 mb-4 flex items-center">
          <ExclamationTriangleIcon class="w-5 h-5 mr-2 text-red-600" />
          Delete Account
        </h3>

        <div class="space-y-4">
          <p class="text-sm text-red-700">
            <strong>Warning:</strong> This action cannot be undone. This will permanently delete your account and remove all your data from our servers.
          </p>

          <!-- Confirmation Checkbox -->
          <div class="flex items-start">
            <div class="flex items-center h-5">
              <input
                id="confirm-delete"
                type="checkbox"
                v-model="confirmDelete"
                class="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
              />
            </div>
            <div class="ml-3 text-sm">
              <label for="confirm-delete" class="text-red-700">
                I understand that this action cannot be undone and will permanently delete my account.
              </label>
            </div>
          </div>

          <!-- Delete Account Button -->
          <button
            @click="deleteAccount"
            :disabled="!confirmDelete || isDeletingAccount"
            class="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="isDeletingAccount" class="inline-flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Deleting Account...
            </span>
            <span v-else>Delete Account</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { apiService } from '../../services/apiService'
import { toast } from '../../composables/useToast'
import {
  UserIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()

// State
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const confirmDelete = ref(false)
const isChangingPassword = ref(false)
const isDeletingAccount = ref(false)
const message = ref('')
const messageType = ref('') // 'success' | 'error'

// Computed
const canChangePassword = computed(() => {
  return currentPassword.value.trim() &&
         newPassword.value.trim().length >= 8 &&
         confirmPassword.value.trim() &&
         newPassword.value === confirmPassword.value
})

const messageTypeClass = computed(() => {
  return messageType.value === 'success'
    ? 'bg-green-50 border border-green-200 text-green-800'
    : 'bg-red-50 border border-red-200 text-red-800'
})

// Message functions
function showMessage(text, type) {
  message.value = text
  messageType.value = type
}

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

// Change password function
async function changePassword() {
  if (!canChangePassword.value) return

  clearMessage()
  isChangingPassword.value = true

  try {
    await apiService.changePassword(
      currentPassword.value.trim(),
      newPassword.value.trim()
    )

    showMessage('Password changed successfully!', 'success')

    // Clear form
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''

    toast.success('Password Changed', 'Your password has been updated successfully.')

  } catch (error) {
    console.error('❌ Failed to change password:', error)

    let errorMessage = 'Failed to change password. Please try again.'
    if (error.response?.status === 400) {
      errorMessage = error.response?.data?.detail || 'Invalid current password or new password requirements not met.'
    } else if (error.response?.status === 401) {
      errorMessage = 'Current password is incorrect.'
    }

    showMessage(errorMessage, 'error')
  } finally {
    isChangingPassword.value = false
  }
}

// Delete account function
async function deleteAccount() {
  if (!confirmDelete.value) return

  clearMessage()
  isDeletingAccount.value = true

  try {
    await apiService.deleteAccount()

    showMessage('Account deleted successfully. You will be logged out now.', 'success')

    toast.success('Account Deleted', 'Your account has been permanently deleted.')

    // Logout after a short delay - the auth store will handle showing the login modal
    setTimeout(() => {
      authStore.logout()
    }, 2000)

  } catch (error) {
    console.error('❌ Failed to delete account:', error)

    let errorMessage = 'Failed to delete account. Please try again.'
    if (error.response?.status === 400) {
      errorMessage = error.response?.data?.detail || 'Unable to delete account at this time.'
    }

    showMessage(errorMessage, 'error')
  } finally {
    isDeletingAccount.value = false
  }
}
</script>