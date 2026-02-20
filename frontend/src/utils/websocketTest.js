// WebSocket testing utilities for development
export const testWebSocketConnection = async (userId = 'test_user') => {
  console.debug('🧪 Testing WebSocket connection...')

  try {
    // Import the WebSocket service
    const { settingsWebSocket } = await import('../services/websocketService')

    // Setup test handlers
    let connectionResult = null
    let progressUpdates = []
    let errorOccurred = null
    let completionResult = null

    settingsWebSocket.onProgress((data) => {
      console.debug('📊 Progress update:', data)
      progressUpdates.push(data)
    })

    settingsWebSocket.onComplete((result) => {
      console.debug('✅ Test completed:', result)
      completionResult = result
    })

    settingsWebSocket.onError((error) => {
      console.error('❌ Test error:', error)
      errorOccurred = error
    })

    settingsWebSocket.onConnection((connected) => {
      console.debug('🔗 Connection state changed:', connected ? 'Connected' : 'Disconnected')
    })

    // Mock backend connection acknowledgment and progress messages for testing
    setTimeout(() => {
      console.debug('🧪 Simulating backend connection acknowledgment...')

      // First send connection acknowledgment
      settingsWebSocket.testHandleMessage({
        type: 'connected',
        message: 'Connected to Inquira processing service',
        timestamp: new Date().toISOString()
      })

      // Then simulate progress messages
      setTimeout(() => {
        console.debug('🧪 Simulating backend progress messages...')

        const mockMessages = [
          { type: 'progress', stage: 'starting', message: '🚀 Starting data processing pipeline...', timestamp: new Date().toISOString() },
          { type: 'progress', stage: 'converting', progress: 25, message: '📊 Converting file to DuckDB database...', fact: '📊 Did you know? The first database was created in 1960', timestamp: new Date().toISOString() },
          { type: 'progress', stage: 'converting', progress: 75, message: '⚙️ Optimizing database structure...', fact: '🔢 Statistics show 2.5 quintillion bytes of data are created daily', timestamp: new Date().toISOString() },
          { type: 'progress', stage: 'generating_schema', progress: 90, message: '🧠 Analyzing data structure...', fact: '📈 Machine learning models can process millions of data points per second', timestamp: new Date().toISOString() },
          { type: 'completed', result: { success: true, message: '🎉 All processing steps completed successfully!' }, timestamp: new Date().toISOString() }
        ]

        mockMessages.forEach((msg, index) => {
          setTimeout(() => {
            // Simulate receiving message from WebSocket
            settingsWebSocket.testHandleMessage(msg)
          }, index * 2000)
        })
      }, 500)
    }, 1000)

    // Attempt connection
    console.debug('🔌 Connecting to WebSocket...')
    await settingsWebSocket.connect(userId)
    connectionResult = 'connected'

    // Send test data
    console.debug('📤 Sending test settings data...')
    const testSettings = {
      api_key: 'test_api_key_123',
      data_path: '/test/data.csv',
      context: 'Test context for data analysis',
      selected_model: 'gemini-2.5-flash'
    }

    settingsWebSocket.startSettingsSave(testSettings)

    // Return test results
    return {
      connection: connectionResult,
      progressUpdates,
      error: errorOccurred,
      completion: completionResult
    }

  } catch (error) {
    console.error('❌ WebSocket test failed:', error)
    return {
      connection: 'failed',
      error: error.message,
      progressUpdates: [],
      completion: null
    }
  }
}

// Test function that can be called from browser console
window.testWebSocket = testWebSocketConnection

// Test backend connectivity and authentication
window.testBackendConnection = async () => {
  console.debug('🔍 Testing backend connection and authentication...')

  try {
    // Import API service
    const { apiService } = await import('../services/apiService')

    // Test 1: Health check
    console.debug('🏥 Testing backend health...')
    try {
      const health = await apiService.healthCheck()
      console.debug('✅ Backend is healthy:', health)
    } catch (error) {
      console.error('❌ Backend health check failed:', error.response?.status, error.response?.data)
      return { success: false, error: 'Backend not accessible' }
    }

    // Test 2: Authentication check
    console.debug('🔐 Testing authentication...')
    try {
      const auth = await apiService.verifyAuth()
      console.debug('✅ Authentication successful:', auth)
    } catch (error) {
      console.error('❌ Authentication failed:', error.response?.status, error.response?.data)
      return { success: false, error: 'Authentication failed', status: error.response?.status }
    }

    // Test 3: Settings endpoint
    console.debug('⚙️ Testing settings endpoint...')
    try {
      const settings = await apiService.getSettings()
      console.debug('✅ Settings retrieved:', settings)
    } catch (error) {
      console.error('❌ Settings retrieval failed:', error.response?.status, error.response?.data)
      return { success: false, error: 'Settings endpoint failed', status: error.response?.status }
    }

    console.debug('🎉 All backend tests passed!')
    return { success: true, message: 'Backend connection and authentication working' }

  } catch (error) {
    console.error('❌ Backend test failed:', error)
    return { success: false, error: error.message }
  }
}

console.debug('🧪 Test utilities loaded:')
console.debug('  - testWebSocket() - Test WebSocket connection')
console.debug('  - testBackendConnection() - Test backend connectivity and auth')