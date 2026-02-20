import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')

// Load WebSocket test utilities in development
if (import.meta.env.DEV) {
  import('./utils/websocketTest.js')
}
