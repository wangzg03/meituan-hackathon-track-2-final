import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Evaluation from '@/views/Evaluation.vue'
import Records from '@/views/Records.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: Home
    },
    {
      path: '/evaluation',
      name: 'Evaluation',
      component: Evaluation
    },
    {
      path: '/records',
      name: 'Records',
      component: Records
    }
  ]
})

export default router