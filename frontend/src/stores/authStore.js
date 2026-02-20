import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '../services/apiService'
import { settingsWebSocket } from '../services/websocketService'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const error = ref('')

  // Computed
  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.user_id || '')

  // Actions
  async function checkAuth() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const result = await apiService.verifyAuth()
      if (result && result.user) {
        user.value = result.user
        isAuthenticated.value = true
      } else {
        user.value = null
        isAuthenticated.value = false
      }
    } catch (err) {
      user.value = null
      isAuthenticated.value = false
      // Don't set error.value for auth check failures - this is expected for unauthenticated users
    } finally {
      isLoading.value = false
    }
  }

  async function login(username, password) {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const result = await apiService.login(username, password)
      user.value = {
        user_id: result.user_id,
        username: username
      }
      isAuthenticated.value = true
      error.value = ''
      return true
    } catch (error) {
      console.error('❌ Login failed:', error)
      // Provide user-friendly error message
      if (error.response?.status === 401) {
        error.value = 'Invalid username or password. Please check your credentials and try again.'
      } else if (error.response?.status === 429) {
        error.value = 'Too many login attempts. Please wait a few minutes before trying again.'
      } else if (error.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else {
        error.value = error.response?.data?.detail || 'Login failed. Please check your connection and try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function register(username, password) {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const result = await apiService.register(username, password)
      return true
    } catch (error) {
      console.error('❌ Registration failed:', error)
      // Provide user-friendly error message
      if (error.response?.status === 400) {
        error.value = 'Username already exists or invalid credentials. Please choose a different username.'
      } else if (error.response?.status === 429) {
        error.value = 'Too many registration attempts. Please wait a few minutes before trying again.'
      } else if (error.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else {
        error.value = error.response?.data?.detail || 'Registration failed. Please check your connection and try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    if (isLoading.value) return

    isLoading.value = true

    try {
      await apiService.logout()

      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      user.value = null
      isAuthenticated.value = false
      error.value = ''
    } catch (error) {
      console.error('❌ Logout failed:', error)

      // Even if logout fails on server, clear local state and disconnect WebSocket
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      user.value = null
      isAuthenticated.value = false
    } finally {
      isLoading.value = false
    }
  }

  async function changePassword(currentPassword, newPassword, confirmPassword) {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const result = await apiService.changePassword(currentPassword, newPassword, confirmPassword)
      return true
    } catch (error) {
      console.error('❌ Password change failed:', error)
      // Provide user-friendly error message
      if (error.response?.status === 400) {
        error.value = error.response?.data?.detail || 'Invalid current password or passwords do not match.'
      } else if (error.response?.status === 401) {
        error.value = 'Authentication required. Please log in again.'
      } else if (error.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else {
        error.value = error.response?.data?.detail || 'Password change failed. Please try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function deleteAccount(confirmationText, currentPassword) {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const result = await apiService.deleteAccount(confirmationText, currentPassword)

      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      // Clear local state immediately
      user.value = null
      isAuthenticated.value = false
      error.value = ''

      return true
    } catch (error) {
      console.error('❌ Account deletion failed:', error)

      // Even on failure, disconnect WebSocket if account deletion succeeded partially
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      // Provide user-friendly error message
      if (error.response?.status === 400) {
        error.value = error.response?.data?.detail || 'Invalid confirmation text or password.'
      } else if (error.response?.status === 401) {
        error.value = 'Authentication required. Please log in again.'
      } else if (error.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else {
        error.value = error.response?.data?.detail || 'Account deletion failed. Please try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  function clearError() {
    error.value = ''
  }

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,

    // Computed
    username,
    userId,

    // Actions
    checkAuth,
    login,
    register,
    logout,
    changePassword,
    deleteAccount,
    clearError
  }
})