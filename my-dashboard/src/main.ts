import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './index.css'

// Frappe UI
import {
  Button,
  Badge,
  Dialog,
  Avatar,
  Dropdown,
  LoadingIndicator,
  setConfig,
  frappeRequest
} from 'frappe-ui'

const app = createApp(App)

// Pinia — State Management
const pinia = createPinia()
app.use(pinia)

// Router
app.use(router)

// Frappe UI Config
setConfig('resourceFetcher', frappeRequest)

// Global Components
app.component('Button', Button)
app.component('Badge', Badge)
app.component('Dialog', Dialog)
app.component('Avatar', Avatar)
app.component('Dropdown', Dropdown)
app.component('LoadingIndicator', LoadingIndicator)

app.mount('#app')