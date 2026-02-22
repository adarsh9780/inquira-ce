import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'


// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    vue(),
    tailwindcss()
  ],
  esbuild: {
    // drop: ['console', 'debugger']
  },
  define: {
    global: 'globalThis',
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
      'axios',
      '@heroicons/vue',
      '@headlessui/vue',
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
    },
    proxy: {
      '/upload': 'http://localhost:8000',
      '/analyze': 'http://localhost:8000',
      '/execute': 'http://localhost:8000',
      '/export': 'http://localhost:8000',
      '/log': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
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
    outDir: '../src/inquira/frontend/dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1000, // Increase warning limit to 1000kb
    rollupOptions: {
      output: {
        manualChunks: {
          // Core Vue ecosystem
          'vue-vendor': ['vue', '@vue/devtools-api'],
          'pinia-store': ['pinia'],

          // UI Libraries
          'ui-components': ['ag-grid-community', 'ag-grid-vue3'],
          'ui-icons': ['@heroicons/vue'],
          'ui-headless': ['@headlessui/vue'],


          // Data Visualization
          'plotly-charts': ['plotly.js-dist-min'],

          // HTTP & Utilities
          'axios-http': ['axios'],
          'utils': ['markdown-it', 'dompurify'],

          // Large third-party libraries (add as needed)
          // 'vendor-large': ['@codemirror/theme-one-dark', '@codemirror/commands']
        }
      }
    }
  }
})
