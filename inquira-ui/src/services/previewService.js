import { apiService } from './apiService'
import { cacheService } from './cacheService'

class PreviewService {
  constructor() {
    this.cacheExpiry = 10 * 60 * 1000 // 10 minutes for preview data
    this.schemaCacheExpiry = 15 * 60 * 1000 // 15 minutes for schema data
  }

  // Get data preview with caching
  async getDataPreview(sampleType = 'random', forceRefresh = false) {
    const cacheKey = cacheService.generateKey('data/preview', { sampleType })

    if (forceRefresh) {
      return cacheService.refresh(cacheKey,
        () => apiService.getDataPreview(sampleType),
        this.cacheExpiry
      )
    }

    return cacheService.getOrSet(cacheKey,
      () => apiService.getDataPreview(sampleType),
      this.cacheExpiry
    )
  }

  // Load schema with caching
  async loadSchema(filepath, forceRefresh = false) {
    const cacheKey = cacheService.generateKey('schema/load', { filepath })

    if (forceRefresh) {
      return cacheService.refresh(cacheKey,
        () => apiService.loadSchema(filepath),
        this.schemaCacheExpiry
      )
    }

    return cacheService.getOrSet(cacheKey,
      () => apiService.loadSchema(filepath),
      this.schemaCacheExpiry
    )
  }

  // Generate schema with caching (more careful with this one as it's expensive)
  async generateSchema(filepath, context = null, forceRefresh = false) {
    const cacheKey = cacheService.generateKey('schema/generate', {
      filepath,
      context: context || ''
    })

    if (forceRefresh) {
      return cacheService.refresh(cacheKey,
        () => apiService.generateSchema(filepath, context),
        this.schemaCacheExpiry
      )
    }

    return cacheService.getOrSet(cacheKey,
      () => apiService.generateSchema(filepath, context),
      this.schemaCacheExpiry
    )
  }

  // Get settings (cached for shorter time)
  async getSettings(forceRefresh = false) {
    const cacheKey = cacheService.generateKey('settings/view')

    if (forceRefresh) {
      return cacheService.refresh(cacheKey,
        () => apiService.getSettings(),
        2 * 60 * 1000 // 2 minutes for settings
      )
    }

    return cacheService.getOrSet(cacheKey,
      () => apiService.getSettings(),
      2 * 60 * 1000 // 2 minutes for settings
    )
  }

  // Clear all preview-related cache
  clearPreviewCache() {
    // Clear data preview cache
    const dataPreviewKeys = Array.from(cacheService.cache.keys())
      .filter(key => key.startsWith('data/preview:'))

    dataPreviewKeys.forEach(key => cacheService.delete(key))

    // Clear schema cache
    const schemaKeys = Array.from(cacheService.cache.keys())
      .filter(key => key.startsWith('schema/'))

    schemaKeys.forEach(key => cacheService.delete(key))

    console.log(`🗑️ Cleared ${dataPreviewKeys.length} data preview and ${schemaKeys.length} schema cache entries`)
  }

  // Clear cache for specific filepath
  clearCacheForFile(filepath) {
    const keysToDelete = []

    // Find all cache keys related to this filepath
    for (const [key] of cacheService.cache) {
      if (key.includes(filepath)) {
        keysToDelete.push(key)
      }
    }

    keysToDelete.forEach(key => cacheService.delete(key))
    console.log(`🗑️ Cleared ${keysToDelete.length} cache entries for file: ${filepath}`)
  }

  // Get cache statistics
  getCacheStats() {
    return cacheService.getStats()
  }
}

// Create singleton instance
export const previewService = new PreviewService()
export default previewService