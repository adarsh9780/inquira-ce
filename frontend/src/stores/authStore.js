import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '../services/apiService'
import { settingsWebSocket } from '../services/websocketService'

export const useAuthStore = defineStore('auth', () => {
  const AUTH_PROBE_TIMEOUT_MS = 15000
  const AUTH_ACTION_TIMEOUT_MS = 30000

  // State
  const user = ref(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const error = ref('')
  const plan = ref('FREE')
  let authProbeRevision = 0

  // Computed
  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.user_id || '')
  const planLabel = computed(() => String(plan.value || 'FREE').toUpperCase())

  async function withTimeout(promise, timeoutMs, message) {
    let timer = null
    try {
      return await Promise.race([
        promise,
        new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error(message)), timeoutMs)
        }),
      ])
    } finally {
      if (timer) clearTimeout(timer)
    }
  }

  async function refreshPlan() {
    try {
      const profile = await withTimeout(
        apiService.v1GetCurrentUser({ timeout: AUTH_PROBE_TIMEOUT_MS }),
        AUTH_PROBE_TIMEOUT_MS + 1000,
        'Profile refresh timed out.',
      )
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
    const probeRevision = ++authProbeRevision
    error.value = ''

    try {
      const profile = await withTimeout(
        apiService.v1GetCurrentUser({ timeout: AUTH_PROBE_TIMEOUT_MS }),
        AUTH_PROBE_TIMEOUT_MS + 1000,
        'Authentication check timed out.',
      )
      if (probeRevision !== authProbeRevision) return
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
    } catch (_err) {
      if (probeRevision !== authProbeRevision) return
      user.value = null
      isAuthenticated.value = false
      plan.value = 'FREE'
      // Don't set error.value for auth check failures - this is expected for unauthenticated users
    }
  }

  async function login(username, password) {
    if (isLoading.value) return

    authProbeRevision += 1
    isLoading.value = true
    error.value = ''

    try {
      const result = await withTimeout(
        apiService.v1Login(username, password),
        AUTH_ACTION_TIMEOUT_MS,
        'Login request timed out.',
      )
      user.value = {
        user_id: result.user_id,
        username: result.username || username
      }
      isAuthenticated.value = true
      plan.value = result.plan || 'FREE'
      error.value = ''
      return true
    } catch (err) {
      console.error('❌ Login failed:', err)
      // Provide user-friendly error message
      if (err.response?.status === 401) {
        error.value = 'Invalid username or password. Please check your credentials and try again.'
      } else if (err.response?.status === 429) {
        error.value = 'Too many login attempts. Please wait a few minutes before trying again.'
      } else if (err.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Login timed out. Please check backend connectivity and try again.'
      } else {
        error.value = err.response?.data?.detail || 'Login failed. Please check your connection and try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function register(username, password) {
    if (isLoading.value) return

    authProbeRevision += 1
    isLoading.value = true
    error.value = ''

    try {
      const result = await withTimeout(
        apiService.v1Register(username, password),
        AUTH_ACTION_TIMEOUT_MS,
        'Registration request timed out.',
      )
      user.value = {
        user_id: result.user_id,
        username: result.username || username
      }
      isAuthenticated.value = true
      plan.value = result.plan || 'FREE'
      error.value = ''
      return true
    } catch (err) {
      console.error('❌ Registration failed:', err)
      // Provide user-friendly error message
      if (err.response?.status === 400) {
        error.value = 'Username already exists or invalid credentials. Please choose a different username.'
      } else if (err.response?.status === 429) {
        error.value = 'Too many registration attempts. Please wait a few minutes before trying again.'
      } else if (err.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Registration timed out. Please check backend connectivity and try again.'
      } else {
        error.value = err.response?.data?.detail || 'Registration failed. Please check your connection and try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    if (isLoading.value) return

    authProbeRevision += 1
    isLoading.value = true

    try {
      await withTimeout(
        apiService.v1Logout(),
        AUTH_ACTION_TIMEOUT_MS,
        'Logout request timed out.',
      )

      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      user.value = null
      isAuthenticated.value = false
      plan.value = 'FREE'
      error.value = ''
    } catch (err) {
      console.error('❌ Logout failed:', err)

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
      await withTimeout(
        apiService.changePassword(currentPassword, newPassword, confirmPassword),
        AUTH_ACTION_TIMEOUT_MS,
        'Password change request timed out.',
      )
      return true
    } catch (err) {
      console.error('❌ Password change failed:', err)
      // Provide user-friendly error message
      if (err.response?.status === 400) {
        error.value = err.response?.data?.detail || 'Invalid current password or passwords do not match.'
      } else if (err.response?.status === 401) {
        error.value = 'Authentication required. Please log in again.'
      } else if (err.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Password change timed out. Please try again.'
      } else {
        error.value = err.response?.data?.detail || 'Password change failed. Please try again.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function deleteAccount(confirmationText, currentPassword) {
    if (isLoading.value) return

    authProbeRevision += 1
    isLoading.value = true
    error.value = ''

    try {
      await withTimeout(
        apiService.deleteAccount(confirmationText, currentPassword),
        AUTH_ACTION_TIMEOUT_MS,
        'Account deletion request timed out.',
      )

      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      // Clear local state immediately
      user.value = null
      isAuthenticated.value = false
      plan.value = 'FREE'
      error.value = ''

      return true
    } catch (err) {
      console.error('❌ Account deletion failed:', err)

      // Even on failure, disconnect WebSocket if account deletion succeeded partially
      if (settingsWebSocket.isPersistentMode) {
        settingsWebSocket.disconnectPersistent()
      }

      // Provide user-friendly error message
      if (err.response?.status === 400) {
        error.value = err.response?.data?.detail || 'Invalid confirmation text or password.'
      } else if (err.response?.status === 401) {
        error.value = 'Authentication required. Please log in again.'
      } else if (err.response?.status >= 500) {
        error.value = 'Server error. Please try again later.'
      } else if (String(err?.message || '').toLowerCase().includes('timed out')) {
        error.value = 'Account deletion timed out. Please try again.'
      } else {
        error.value = err.response?.data?.detail || 'Account deletion failed. Please try again.'
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
