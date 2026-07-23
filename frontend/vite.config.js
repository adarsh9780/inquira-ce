import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = fileURLToPath(new URL('.', import.meta.url))
const frontendPackage = JSON.parse(
  readFileSync(resolve(frontendRoot, 'package.json'), 'utf-8')
)
const frontendVersion = String(frontendPackage.version || '0.0.0').trim() || '0.0.0'

const manualChunkGroups = {
  'vue-vendor': ['node_modules/vue/', 'node_modules/@vue/devtools-api/'],
  'pinia-store': ['node_modules/pinia/'],
  'table-engine': ['node_modules/@tanstack/table-core/', 'node_modules/@tanstack/vue-table/'],
  'ui-icons': ['node_modules/@heroicons/vue/'],
  'ui-primitives': ['node_modules/reka-ui/', 'node_modules/@internationalized/'],
  'plotly-charts': ['node_modules/plotly.js-dist-min/'],
  'utils': ['node_modules/markdown-it/', 'node_modules/dompurify/'],
}

function manualChunks(id) {
  const normalizedId = String(id || '').replaceAll('\\', '/')
  for (const [chunkName, packagePaths] of Object.entries(manualChunkGroups)) {
    if (packagePaths.some((packagePath) => normalizedId.includes(packagePath))) {
      return chunkName
    }
  }
  return undefined
}
// https://vite.dev/config/
export default defineConfig({
  envDir: '..',
  envPrefix: ['VITE_'],
  base: './',
  plugins: [
    vue(),
    tailwindcss()
  ],
  define: {
    global: 'globalThis',
    __APP_VERSION__: JSON.stringify(frontendVersion),
  },
  optimizeDeps: {
    include: [
      'codemirror',
      '@codemirror/state',
      '@codemirror/view',
      '@codemirror/lang-python',
      '@codemirror/autocomplete',
      '@codemirror/search',
      '@codemirror/commands',
      'vue',
      'pinia',
      '@heroicons/vue',
      'reka-ui',
      'markdown-it',
      'dompurify',
      'plotly.js-dist-min'
    ]
  },
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
      'Cross-Origin-Resource-Policy': 'cross-origin'
    }
  },
  preview: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
      'Cross-Origin-Resource-Policy': 'cross-origin'
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    manifest: true,
    chunkSizeWarningLimit: 5000,
    rolldownOptions: {
      checks: {
        pluginTimings: false,
      },
      output: {
        manualChunks,
      }
    }
  }
})
