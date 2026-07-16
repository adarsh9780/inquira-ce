import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..')
const currentPlatform = process.platform
const runId = `${currentPlatform}-${Date.now()}`
const e2eHome = path.join(repoRoot, '.playwright', runId, 'home')

fs.mkdirSync(e2eHome, { recursive: true })

function resolvePlatformProject() {
  if (currentPlatform === 'darwin') {
    return {
      name: 'macos-native',
      use: {
        ...devices['Desktop Safari'],
        browserName: 'webkit',
      },
    }
  }

  if (currentPlatform === 'win32') {
    return {
      name: 'windows-native',
      use: {
        ...devices['Desktop Chrome'],
        browserName: 'chromium',
      },
    }
  }

  return {
    name: 'linux-native',
    use: {
      ...devices['Desktop Chrome'],
      browserName: 'chromium',
    },
  }
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    headless: true,
  },
  projects: [resolvePlatformProject()],
  webServer: [
    {
      command: 'uv run --group dev python main.py',
      cwd: path.join(repoRoot, 'backend'),
      url: 'http://127.0.0.1:8000/health',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
        HOME: e2eHome,
        USERPROFILE: e2eHome,
        APPDATA: path.join(e2eHome, 'AppData'),
        LOCALAPPDATA: path.join(e2eHome, 'LocalAppData'),
        INQUIRA_HOST: '127.0.0.1',
        INQUIRA_PORT: '8000',
        INQUIRA_AUTH_PROVIDER: 'sqlite',
        INQUIRA_ALLOW_SCHEMA_BOOTSTRAP: '1',
        CORS_ORIGINS: 'http://127.0.0.1:4173',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: __dirname,
      url: 'http://127.0.0.1:4173',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
        VITE_E2E: '1',
      },
    },
  ],
})
