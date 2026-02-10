<script setup lang="ts">
import { ref } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import CrmSidebar from '@/components/CrmSidebar.vue'
import UserList from '@/components/UserList.vue'

const isMenuOpen = ref(false)
</script>

<template>
  <div class="flex h-screen w-full bg-white overflow-hidden">
    
    <div v-if="isMenuOpen" 
         @click="isMenuOpen = false"
         class="fixed inset-0 bg-black/40 z-40 lg:hidden">
    </div>

    <aside :class="[
      'fixed inset-y-0 left-0 z-50 w-[260px] bg-white border-r transition-transform duration-300 ease-in-out',
      isMenuOpen ? 'translate-x-0' : '-translate-x-full',
      'lg:relative lg:translate-x-0 lg:flex-shrink-0'
    ]">
      <div class="h-full flex flex-col">
        <div class="p-4 flex justify-end lg:hidden border-b">
          <button @click="isMenuOpen = false" class="p-1 hover:bg-gray-100 rounded">
            <X class="w-6 h-6 text-gray-600" />
          </button>
        </div>
        <CrmSidebar class="flex-1" />
      </div>
    </aside>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-14 flex items-center px-4 border-b bg-white lg:hidden flex-shrink-0">
        <button @click="isMenuOpen = true" class="p-2 -ml-2 hover:bg-gray-100 rounded-md">
          <Menu class="w-6 h-6 text-gray-600" />
        </button>
        <span class="ml-3 font-bold text-gray-800">Frappe CRM</span>
      </header>

      <main class="flex-1 overflow-auto p-0">
        <UserList />
      </main>
    </div>
  </div>
</template>