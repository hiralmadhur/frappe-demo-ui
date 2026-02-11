import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import './index.css'

import { Button, setConfig, frappeRequest, resourcesPlugin,Dropdown } from 'frappe-ui'

let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)

app.component('Button', Button)
app.component('Dropdown', Dropdown)

app.mount('#app')
