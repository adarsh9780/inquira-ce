import {
    BaseDirectory,
    create,
    exists,
    mkdir,
    readTextFile
} from '@tauri-apps/plugin-fs'

const PREFS_DIR = 'preferences'
const PREFS_FILE = `${PREFS_DIR}/ui_preferences.json`
const UI_PREFERENCES_SCOPE = 'ui-preferences'

function wailsApp() {
    if (typeof window === 'undefined') return null
    return window.go?.main?.App || null
}

function loadLegacyBrowserPreferences() {
    if (typeof localStorage === 'undefined') return {}
    try {
        const stored = localStorage.getItem('ui_preferences')
        if (!stored) return {}
        const parsed = JSON.parse(stored)
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    } catch (_error) {
        return {}
    }
}

function isTauriRuntime() {
    return typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
}

async function ensureDirectory() {
    if (!isTauriRuntime()) return
    try {
        await mkdir(PREFS_DIR, { baseDir: BaseDirectory.AppData, recursive: true })
    } catch (e) {
        // Ignore if directory already exists
    }
}

export const uiPreferencesService = {
    async getPreferences() {
        const app = wailsApp()
        if (app?.LoadLocalState) {
            try {
                const nativePreferences = await app.LoadLocalState(UI_PREFERENCES_SCOPE)
                if (nativePreferences && typeof nativePreferences === 'object' && !Array.isArray(nativePreferences)) {
                    return nativePreferences
                }
                const legacyPreferences = loadLegacyBrowserPreferences()
                if (Object.keys(legacyPreferences).length > 0 && app?.SaveLocalState) {
                    const migrated = await app.SaveLocalState(UI_PREFERENCES_SCOPE, legacyPreferences)
                    if (migrated && typeof localStorage !== 'undefined' && typeof localStorage.removeItem === 'function') {
                        localStorage.removeItem('ui_preferences')
                    }
                }
                return legacyPreferences
            } catch (error) {
                console.warn('Failed to load UI preferences through Wails:', error)
                return loadLegacyBrowserPreferences()
            }
        }
        if (!isTauriRuntime()) {
            return loadLegacyBrowserPreferences()
        }

        try {
            const fileExists = await exists(PREFS_FILE, { baseDir: BaseDirectory.AppData })
            if (!fileExists) return {}
            const raw = await readTextFile(PREFS_FILE, { baseDir: BaseDirectory.AppData })
            if (!raw || !raw.trim()) return {}
            return JSON.parse(raw)
        } catch (error) {
            console.warn('Failed to load UI preferences:', error)
            return {}
        }
    },

    async savePreferences(prefs) {
        const app = wailsApp()
        if (app?.SaveLocalState) {
            try {
                return Boolean(await app.SaveLocalState(UI_PREFERENCES_SCOPE, prefs))
            } catch (error) {
                console.warn('Failed to save UI preferences through Wails:', error)
                return false
            }
        }
        if (!isTauriRuntime()) {
            try {
                localStorage.setItem('ui_preferences', JSON.stringify(prefs))
                return true
            } catch (e) {
                return false
            }
        }

        try {
            await ensureDirectory()
            const serialized = JSON.stringify(prefs, null, 2)
            const file = await create(PREFS_FILE, { baseDir: BaseDirectory.AppData })
            try {
                await file.write(new TextEncoder().encode(serialized))
                if (typeof file.sync === 'function') {
                    await file.sync()
                }
            } finally {
                await file.close()
            }
            return true
        } catch (error) {
            console.warn('Failed to save UI preferences:', error)
            return false
        }
    },
}
