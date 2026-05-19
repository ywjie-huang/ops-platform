import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import pinia from './stores'
import { registerIcons } from '@/utils/icons'
import '@/assets/styles/index.scss'

const app = createApp(App)

registerIcons(app)
app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.use(pinia)

app.mount('#app')
