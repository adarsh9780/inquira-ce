<template>
  <!-- Modal Overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto"
    aria-labelledby="modal-title"
    role="dialog"
    aria-modal="true"
  >
    <!-- Background overlay -->
    <div
      class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
      @click="closeModal"
    ></div>

    <!-- Modal container -->
    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="bg-white px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-center">
            <h3 class="text-lg font-semibold text-gray-900" id="modal-title">
              {{ isLoginMode ? 'Sign In' : 'Create Account' }}
            </h3>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="bg-white px-6 py-6">
          <!-- Message Display Area -->
          <div v-if="displayMessage" :class="[
            'mb-4 p-4 rounded-md',
            isErrorMessage ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'
          ]">
            <div class="flex items-center">
              <div v-if="isShowingSuccessSpinner" class="animate-spin rounded-full h-5 w-5 border-b-2 border-green-500 mr-2"></div>
              <CheckCircleIcon v-else-if="!isErrorMessage" class="h-5 w-5 text-green-500 mr-2" />
              <ExclamationTriangleIcon v-else class="h-5 w-5 text-red-500 mr-2" />
              <p :class="[
                'text-sm font-medium',
                isErrorMessage ? 'text-red-800' : 'text-green-800'
              ]">
                {{ displayMessage }}
              </p>
            </div>
          </div>

          <form v-if="!isShowingSuccessSpinner" @submit.prevent="handleSubmit" class="space-y-6">
            <!-- Username Field -->
            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                v-model="formData.username"
                required
                :disabled="authStore.isLoading || isShowingSuccessSpinner"
                placeholder="Enter your username"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <p class="mt-1 text-xs text-gray-500">
                3-50 characters, letters and numbers only
              </p>
            </div>

            <!-- Password Field -->
            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <div class="relative">
                <input
                  id="password"
                  :type="showPassword ? 'text' : 'password'"
                  v-model="formData.password"
                  required
                  :disabled="authStore.isLoading || isShowingSuccessSpinner"
                  :placeholder="isLoginMode ? 'Enter your password' : 'Create a password'"
                  @keydown.enter="handleSubmit"
                  class="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  @click="showPassword = !showPassword"
                  type="button"
                  class="absolute inset-y-0 right-0 pr-3 flex items-center"
                  :disabled="authStore.isLoading || isShowingSuccessSpinner"
                >
                  <EyeIcon v-if="!showPassword" class="h-4 w-4 text-gray-400 hover:text-gray-600" />
                  <EyeSlashIcon v-else class="h-4 w-4 text-gray-400 hover:text-gray-600" />
                </button>
              </div>
              <p class="mt-1 text-xs text-gray-500">
                {{ isLoginMode ? 'Enter your account password' : 'At least 6 characters' }}
              </p>
            </div>

            <!-- Confirm Password Field (only for registration) -->
            <div v-if="!isLoginMode">
              <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                v-model="formData.confirmPassword"
                required
                :disabled="authStore.isLoading || isShowingSuccessSpinner"
                placeholder="Confirm your password"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <p v-if="formData.password && formData.confirmPassword && formData.password !== formData.confirmPassword"
                 class="mt-1 text-xs text-red-600">
                Passwords do not match
              </p>
            </div>

            <!-- Terms & Conditions Agreement -->
            <div v-if="!isLoginMode" class="flex items-start space-x-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-3">
              <input
                id="acceptTerms"
                type="checkbox"
                v-model="formData.acceptTerms"
                :disabled="authStore.isLoading || isShowingSuccessSpinner"
                class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
              />
              <label for="acceptTerms" class="text-xs text-gray-600 leading-5">
                I agree to the
                <a
                  href="/terms-and-conditions.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="font-semibold text-blue-600 hover:text-blue-500"
                >
                  Terms &amp; Conditions
                </a>
                for using Inquira.
              </label>
            </div>
          </form>
        </div>

        <!-- Modal Footer -->
        <div class="bg-gray-50 px-6 py-4 flex flex-col space-y-3">
          <!-- Action Buttons -->
          <div class="flex space-x-3">
            <button
              @click="closeModal"
              :disabled="authStore.isLoading || isShowingSuccessSpinner"
              class="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              @click="handleSubmit"
              :disabled="authStore.isLoading || isShowingSuccessSpinner || !isFormValid"
              class="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div v-if="authStore.isLoading" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              {{ authStore.isLoading ? (isLoginMode ? 'Signing In...' : 'Creating Account...') : (isLoginMode ? 'Sign In' : 'Create Account') }}
            </button>
          </div>

          <!-- Mode Toggle -->
          <div class="text-center">
            <button
              @click="toggleMode"
              :disabled="authStore.isLoading || isShowingSuccessSpinner"
              class="text-sm text-blue-600 hover:text-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ isLoginMode ? "Don't have an account? Sign up" : 'Already have an account? Sign in' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import {
  XMarkIcon,
  EyeIcon,
  EyeSlashIcon,
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
const isLoginMode = ref(true)
const showPassword = ref(false)
const isShowingSuccessSpinner = ref(false)
const message = ref('')
const messageType = ref('') // 'success' or 'error'

const formData = ref({
  username: '',
  password: '',
  confirmPassword: '',
  acceptTerms: false
})

// Computed
const isFormValid = computed(() => {
  if (!formData.value.username.trim() || !formData.value.password.trim()) {
    return false
  }

  if (!isLoginMode.value) {
    return (
      formData.value.password === formData.value.confirmPassword &&
      formData.value.acceptTerms
    )
  }

  return true
})

const displayMessage = computed(() => {
  return message.value || authStore.error
})

const isErrorMessage = computed(() => {
  return authStore.error || (message.value && messageType.value === 'error')
})

// Methods
function closeModal() {
  if (authStore.isLoading) return

  emit('close')
}

function toggleMode() {
  if (authStore.isLoading) return

  isLoginMode.value = !isLoginMode.value
  clearMessage()
  resetForm()
}

function resetForm() {
  formData.value = {
    username: '',
    password: '',
    confirmPassword: '',
    acceptTerms: false
  }
  authStore.clearError() // Clear any previous errors
}

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

function showMessage(text, type) {
  message.value = text
  messageType.value = type

  // Clear message after 5 seconds
  setTimeout(() => {
    message.value = ''
    messageType.value = ''
  }, 5000)
}

async function handleSubmit() {
  if (authStore.isLoading || !isFormValid.value) return

  clearMessage()

  try {
    if (isLoginMode.value) {
      // Login
      const success = await authStore.login(formData.value.username, formData.value.password)

      if (success) {
        showMessage('Login successful! Welcome back.', 'success')
        authStore.clearError() // Clear any previous errors

        // Notify parent so it can run post-auth setup (e.g., WebSocket connect)
        // Emit immediately to avoid race conditions with cookie/session propagation
        // Parent listener: @authenticated="handleAuthenticated"
        emit('authenticated', authStore.user)

        // Close modal after success - the auth store will handle the state update
        setTimeout(() => {
          emit('close')
        }, 1500)
      } else {
        // Login failed - display error message on the card
        console.debug('Login failed with error:', authStore.error)
        // Show the error message directly to ensure it's visible on the card
        if (authStore.error) {
          showMessage(authStore.error, 'error')
        } else {
          showMessage('Login failed. Please try again.', 'error')
        }
      }

    } else {
      // Register
      const success = await authStore.register(formData.value.username, formData.value.password)

      if (success) {
        isShowingSuccessSpinner.value = true
        showMessage('Sign in successful', 'success')
        authStore.clearError() // Clear any previous errors

        // Switch to login mode after successful registration
        setTimeout(() => {
          isShowingSuccessSpinner.value = false
          isLoginMode.value = true
          resetForm()
        }, 2000)
      } else {
        // Registration failed - display error message on the card
        console.debug('Registration failed with error:', authStore.error)
        // Show the error message directly to ensure it's visible on the card
        if (authStore.error) {
          showMessage(authStore.error, 'error')
        } else {
          showMessage('Registration failed. Please try again.', 'error')
        }
      }
    }

  } catch (error) {
    console.error('Auth error:', error)
    // Error is already handled by authStore, no need to show additional message
  }
}

// Watch for modal open/close
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm()
    clearMessage()
    isShowingSuccessSpinner.value = false
  }
})

// Watch for authentication state changes
watch(() => authStore.isAuthenticated, (isAuthenticated) => {
  if (isAuthenticated && props.isOpen) {
    // Close modal when user becomes authenticated
    setTimeout(() => {
      emit('close')
    }, 1500)
  }
})

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && props.isOpen) {
    closeModal()
  }
})
</script>
