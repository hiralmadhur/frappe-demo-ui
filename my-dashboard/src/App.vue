<script setup lang="ts">
import { ref, onMounted, computed, provide } from 'vue'
import { useRouter } from 'vue-router'
import SellerSidebarmenu from '@/components/Seller/SellerSidebarmenu.vue'
import CustomerSidebarmenu from '@/components/Customer/CustomerSidebarmenu.vue'
import SellerNavbar from '@/components/Seller/SellerNavbar.vue'
import CustomerNavbar from '@/components/Customer/CustomerNavbar.vue'
import { X, CheckCircle, AlertCircle } from 'lucide-vue-next'
import { Button } from 'frappe-ui'

const router = useRouter()
const isSidebarOpen = ref(false)
const currentFilters = ref<any>({})
const userRole = ref<'Seller' | 'Customer' | 'Administrator'>('Seller')
const isLoading = ref(true)

const toast = ref({ show: false, message: '', type: 'success' })
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { show: true, message, type }
  setTimeout(() => { toast.value.show = false }, 4000)
}
provide('showToast', showToast)
provide('userRole', userRole)

const applyRole = (role: string) => {
  if (!role || role === 'Guest') {
    window.location.href = '/login'
    return
  }
  userRole.value = role as any

  if (role === 'Administrator') {
    // If Admin is already on a portal route, stay there. Otherwise go to /seller.
    const currentPath = window.location.pathname
    if (!currentPath.includes('/frontend/seller') && !currentPath.includes('/frontend/customer')) {
      router.replace('/seller')
    }
  } else {
    router.replace(role === 'Customer' ? '/customer' : '/seller')
  }

  isLoading.value = false
}

onMounted(async () => {
  try {
    const csrfToken = (window as any)?.frappe?.csrf_token || (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || 'fetch'
    const res = await fetch('/api/method/my_frappe_app.api.get_current_user_role', {
      headers: { 'X-Frappe-CSRF-Token': csrfToken }
    })
    if (!res.ok) { applyRole('Guest'); return }
    const data = await res.json()
    applyRole(data?.message?.role || 'Guest')
  } catch (e) { applyRole('Guest') }
})

const updateFilters = (f: any) => {
  currentFilters.value = f
  if (window.innerWidth < 1024) isSidebarOpen.value = false
}

const isCustomerRoute = computed(() => {
  if (userRole.value === 'Administrator') {
    return router.currentRoute.value.path.startsWith('/customer')
  }
  return userRole.value === 'Customer'
})

const CurrentSidebar = computed(() => isCustomerRoute.value ? CustomerSidebarmenu : SellerSidebarmenu)
const CurrentNavbar = computed(() => isCustomerRoute.value ? CustomerNavbar : SellerNavbar)
</script>

<template>
  <div class="flex h-screen w-screen bg-gray-50 overflow-hidden font-sans relative">
    <Transition name="slide-fade">
      <div v-if="toast.show"
        :class="['fixed top-5 right-5 z-[100] flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl border text-white transition-all', toast.type === 'success' ? 'bg-gray-900 border-gray-800' : 'bg-red-600 border-red-500']">
        <CheckCircle v-if="toast.type === 'success'" class="w-5 h-5 text-green-400" />
        <AlertCircle v-else class="w-5 h-5 text-red-200" />
        <span class="font-bold text-sm">{{ toast.message }}</span>
        <button @click="toast.show = false" class="ml-2 hover:opacity-70">
          <X class="w-4 h-4" />
        </button>
      </div>
    </Transition>

    <div v-if="isLoading" class="flex h-screen w-screen items-center justify-center bg-white">
      <div class="flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-gray-400 font-medium tracking-widest uppercase">Initializing...</p>
      </div>
    </div>

    <template v-else>
      <div v-if="isSidebarOpen" @click="isSidebarOpen = false"
        class="fixed inset-0 bg-black/40 z-[60] lg:hidden backdrop-blur-sm transition-opacity"></div>

      <aside
        :class="['fixed inset-y-0 left-0 z-[70] w-72 bg-white border-r transition-transform duration-300 lg:static lg:translate-x-0', isSidebarOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:translate-x-0']">
        <component :is="CurrentSidebar" :isOpen="isSidebarOpen" @update:filters="updateFilters"
          @close="isSidebarOpen = false" />
      </aside>

      <div class="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <component :is="CurrentNavbar" @toggle-sidebar="isSidebarOpen = !isSidebarOpen" />
        <main class="flex-1 overflow-y-auto bg-[#F9FAFB] custom-scrollbar">
          <router-view :filters="currentFilters" />
        </main>
      </div>
    </template>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #E5E7EB;
  border-radius: 10px;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>