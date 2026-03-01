import { apiService } from './apiService'
import { cacheService } from './cacheService'
import { useAppStore } from '../stores/appStore'
import { inferTableNameFromDataPath } from '../utils/chatBootstrap'

class PreviewService {
  constructor() {
    this.schemaCacheExpiry = 15 * 60 * 1000 // 15 minutes for schema data
  }

  // Load schema with caching
  async loadSchema(filepath, forceRefresh = false, tableNameOverride = null) {
    const appStore = useAppStore()
    const dataPath = filepath || appStore.dataFilePath
    const tableName = (
      tableNameOverride ||
      appStore.ingestedTableName ||
      inferTableNameFromDataPath(dataPath || '')
    ).trim()
    if (!appStore.activeWorkspaceId || !tableName) {
      return { table_name: '', columns: [] }
    }
    const cacheKey = cacheService.generateKey('schema/load', { workspace: appStore.activeWorkspaceId, tableName })
    const fetcher = () => apiService.v1GetDatasetSchema(appStore.activeWorkspaceId, tableName)

    if (forceRefresh) {
      return cacheService.refresh(cacheKey, fetcher, this.schemaCacheExpiry)
    }

    return cacheService.getOrSet(cacheKey, fetcher, this.schemaCacheExpiry)
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

  // Clear schema/settings cache so dataset schema state is reloaded from backend.
  clearSchemaCache() {
    const schemaKeys = Array.from(cacheService.cache.keys())
      .filter(key => key.startsWith('schema/'))

    schemaKeys.forEach(key => cacheService.delete(key))

    // Also clear settings cache to ensure fresh data path is loaded
    const settingsKeys = Array.from(cacheService.cache.keys())
      .filter(key => key.startsWith('settings/'))

    settingsKeys.forEach(key => cacheService.delete(key))

    console.debug(`🗑️ Cleared ${schemaKeys.length} schema and ${settingsKeys.length} settings cache entries`)
  }

  // Backward-compat alias while call sites migrate.
  clearPreviewCache() {
    this.clearSchemaCache()
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
    console.debug(`🗑️ Cleared ${keysToDelete.length} cache entries for file: ${filepath}`)
  }

  // Get cache statistics
  getCacheStats() {
    return cacheService.getStats()
  }
}

// Create singleton instance
export const previewService = new PreviewService()
export default previewService
