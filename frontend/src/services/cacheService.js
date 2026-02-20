class CacheService {
  constructor() {
    this.cache = new Map()
    this.cacheExpiry = new Map()
    this.defaultExpiry = 5 * 60 * 1000 // 5 minutes
  }

  // Generate cache key
  generateKey(endpoint, params = {}) {
    const sortedParams = Object.keys(params)
      .sort()
      .map(key => `${key}:${params[key]}`)
      .join('|')
    return `${endpoint}:${sortedParams}`
  }

  // Set cache entry
  set(key, data, expiryMs = this.defaultExpiry) {
    this.cache.set(key, data)
    this.cacheExpiry.set(key, Date.now() + expiryMs)
  }

  // Get cache entry
  get(key) {
    if (this.cacheExpiry.get(key) < Date.now()) {
      this.delete(key)
      return null
    }
    return this.cache.get(key)
  }

  // Check if cache entry exists and is valid
  has(key) {
    if (!this.cache.has(key)) return false
    if (this.cacheExpiry.get(key) < Date.now()) {
      this.delete(key)
      return false
    }
    return true
  }

  // Delete cache entry
  delete(key) {
    this.cache.delete(key)
    this.cacheExpiry.delete(key)
  }

  // Clear all cache
  clear() {
    this.cache.clear()
    this.cacheExpiry.clear()
  }

  // Get or set cache entry
  async getOrSet(key, fetcher, expiryMs = this.defaultExpiry) {
    if (this.has(key)) {
      console.log(`📋 Cache hit for: ${key}`)
      return this.get(key)
    }

    console.log(`🔄 Cache miss for: ${key}, fetching fresh data`)
    try {
      const data = await fetcher()
      this.set(key, data, expiryMs)
      return data
    } catch (error) {
      console.error(`❌ Failed to fetch data for cache key: ${key}`, error)
      throw error
    }
  }

  // Force refresh cache entry
  async refresh(key, fetcher, expiryMs = this.defaultExpiry) {
    console.log(`🔄 Force refresh for: ${key}`)
    try {
      const data = await fetcher()
      this.set(key, data, expiryMs)
      return data
    } catch (error) {
      console.error(`❌ Failed to refresh data for cache key: ${key}`, error)
      throw error
    }
  }

  // Get cache stats
  getStats() {
    const now = Date.now()
    let validEntries = 0
    let expiredEntries = 0

    for (const [key, expiry] of this.cacheExpiry) {
      if (expiry > now) {
        validEntries++
      } else {
        expiredEntries++
      }
    }

    return {
      totalEntries: this.cache.size,
      validEntries,
      expiredEntries
    }
  }
}

// Create singleton instance
export const cacheService = new CacheService()
export default cacheService