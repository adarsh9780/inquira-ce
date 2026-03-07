import {
    BaseDirectory,
    create,
    exists,
    mkdir,
    readTextFile
} from '@tauri-apps/plugin-fs'

const PREFS_DIR = 'preferences'
const PREFS_FILE = `${PREFS_DIR}/ui_preferences.json`

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
        if (!isTauriRuntime()) {
            try {
                const stored = localStorage.getItem('ui_preferences')
                return stored ? JSON.parse(stored) : {}
            } catch (e) {
                return {}
            }
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

    async hasSeenWalkthrough() {
        const prefs = await this.getPreferences()
        return !!prefs.hasSeenWalkthrough
    },

    async markWalkthroughAsSeen() {
        const prefs = await this.getPreferences()
        prefs.hasSeenWalkthrough = true
        await this.savePreferences(prefs)
    }
}
