import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import FactorView from '../views/FactorView.vue'
import PredictView from '../views/PredictView.vue'
import AnomalyView from '../views/AnomalyView.vue'
import ChatView from '../views/ChatView.vue'

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  { path: '/factor', name: 'Factor', component: FactorView },
  { path: '/predict', name: 'Predict', component: PredictView },
  { path: '/anomaly', name: 'Anomaly', component: AnomalyView },
  { path: '/chat', name: 'Chat', component: ChatView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
