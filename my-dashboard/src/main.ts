import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import './index.css'
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui'

const app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

// FrappeUI already includes resourcesPlugin internally
// DO NOT add app.use(resourcesPlugin) separately — causes "Plugin already applied" warning
app.use(router)
app.use(FrappeUI)

app.mount('#app')