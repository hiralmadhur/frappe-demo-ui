<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import Navbar from '@/components/Navbar.vue'
import Home from '@/pages/Home.vue'
import { X } from 'lucide-vue-next'
import { Button } from 'frappe-ui'

const isSidebarOpen = ref(false)
const currentFilters = ref({ customer: '' })

const updateFilters = (f: any) => {
  currentFilters.value = f
  if (window.innerWidth < 1024) isSidebarOpen.value = false
}
</script>

<template>
  <div class="flex h-screen w-screen bg-gray-50 overflow-hidden">
    <div v-if="isSidebarOpen" @click="isSidebarOpen = false" class="fixed inset-0 bg-black/30 z-40 lg:hidden"></div>

    <aside :class="[
      'fixed inset-y-0 left-0 z-50 w-72 bg-white border-r transition-transform duration-300 lg:static lg:translate-x-0',
      isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
    ]">
      <div class="flex items-center justify-between p-4 lg:hidden border-b bg-gray-50">
        <span class="font-bold">Filters</span>
        <Button variant="ghost" @click="isSidebarOpen = false"><X class="w-5 h-5"/></Button>
      </div>
      <Sidebar @update:filters="updateFilters" />
    </aside>

    <div class="flex-1 flex flex-col min-w-0 h-full">
      <Navbar @toggle-sidebar="isSidebarOpen = !isSidebarOpen" />
      <main class="flex-1 overflow-y-auto p-4 md:p-8">
        <Home :filters="currentFilters" />
      </main>
    </div>
  </div>
</template>