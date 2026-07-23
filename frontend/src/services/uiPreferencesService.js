const UI_PREFERENCES_SCOPE = 'ui-preferences'

function wailsApp() {
    if (typeof window === 'undefined') return null
    return window.go?.main?.App || null
}

function loadBrowserPreferences() {
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

export const uiPreferencesService = {
    async getPreferences() {
        const app = wailsApp()
        if (app?.LoadLocalState) {
            try {
                const nativePreferences = await app.LoadLocalState(UI_PREFERENCES_SCOPE)
                if (nativePreferences && typeof nativePreferences === 'object' && !Array.isArray(nativePreferences)) {
                    return nativePreferences
                }
                return {}
            } catch (error) {
                console.warn('Failed to load UI preferences through Wails:', error)
                return {}
            }
        }
        return loadBrowserPreferences()
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
        try {
            localStorage.setItem('ui_preferences', JSON.stringify(prefs))
            return true
        } catch (_error) {
            return false
        }
    },
}
