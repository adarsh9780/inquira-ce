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
  const plan = ref('FREE')

  // Computed
  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.user_id || '')
  const planLabel = computed(() => String(plan.value || 'FREE').toUpperCase())

  async function refreshPlan() {
    try {
      const profile = await apiService.v1GetCurrentUser()
      if (profile?.plan) {
        plan.value = profile.plan
      }
    } catch (_err) {
      if (!plan.value) {
        plan.value = 'FREE'
      }
    }
  }

  // Actions
  async function checkAuth() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = ''

    try {
      const profile = await apiService.v1GetCurrentUser()
      if (profile && profile.user_id) {
        user.value = {
          user_id: profile.user_id,
          username: profile.username
        }
        isAuthenticated.value = true
        plan.value = profile.plan || 'FREE'
      } else {
        user.value = null
        isAuthenticated.value = false
        plan.value = 'FREE'
      }
    } catch (err) {
      user.value = null
      isAuthenticated.value = false
      plan.value = 'FREE'
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
      const result = await apiService.v1Login(username, password)
      user.value = {
        user_id: result.user_id,
        username: result.username || username
      }
      isAuthenticated.value = true
      plan.value = result.plan || 'FREE'
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
      const result = await apiService.v1Register(username, password)
      user.value = {
        user_id: result.user_id,
        username: result.username || username
      }
      isAuthenticated.value = true
      plan.value = result.plan || 'FREE'
      error.value = ''
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
      await apiService.v1Logout()

      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      user.value = null
      isAuthenticated.value = false
      plan.value = 'FREE'
      error.value = ''
    } catch (error) {
      console.error('❌ Logout failed:', error)

      // Even if logout fails on server, clear local state and disconnect WebSocket
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      user.value = null
      isAuthenticated.value = false
      plan.value = 'FREE'
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
      plan.value = 'FREE'
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
    plan,

    // Computed
    username,
    userId,
    planLabel,

    // Actions
    checkAuth,
    login,
    register,
    logout,
    refreshPlan,
    changePassword,
    deleteAccount,
    clearError
  }
})
