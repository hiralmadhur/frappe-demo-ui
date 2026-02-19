import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/seller'
  },
  // Frappe default redirect after login
  {
    path: '/desk',
    redirect: '/seller'
  },
  {
    path: '/seller',
    name: 'Seller',
    //component: () => import('@/pages/Seller/SellerHome.vue'),
    component: () => import('@/pages/Seller/SellerHomeComponent.vue'),
  },
  {
    path: '/customer',
    name: 'Customer',
    component: () => import('@/pages/Customer/CustomerHome.vue'),
  },
  // NOTE: No catch-all redirect here!
  // A catch-all → /seller was overriding App.vue's router.replace('/customer')
  // because Vue Router processes redirects before the component mounts.
]

const router = createRouter({
  history: createWebHistory('/frontend'),
  routes,
})

export default router