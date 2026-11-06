import './styles.css'
import { createApp } from 'vue'
import App from './App.vue'
import { syncDocument } from './i18n/index.js'

syncDocument()
createApp(App).mount('#app')
