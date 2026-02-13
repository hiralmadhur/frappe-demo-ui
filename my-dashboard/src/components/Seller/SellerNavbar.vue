<script setup lang="ts">
import { Dropdown, Avatar, Button } from 'frappe-ui'
import { LogOut, Menu, Bell } from 'lucide-vue-next'

const emit = defineEmits(['toggle-sidebar'])

const handleLogout = () => {
  // Use standard location redirect to avoid TS errors on custom window properties
  window.location.assign('/login')
}
</script>

<template>
  <nav class="h-16 border-b bg-white/80 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-[50]">
    <div class="flex items-center gap-3">
      <Button variant="ghost" class="lg:hidden p-2" @click="emit('toggle-sidebar')">
        <Menu class="w-5 h-5 text-gray-600" />
      </Button>
      <div class="flex items-center gap-2">
        <div class="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center text-white font-black shadow-lg shadow-blue-100">S</div>
        <h1 class="font-black text-gray-900 text-lg tracking-tight hidden sm:block">Seller Portal</h1>
      </div>
    </div>
    
    <div class="flex items-center gap-4">
      <Button variant="ghost" class="p-2 text-gray-400 hover:bg-gray-50"><Bell class="w-5 h-5" /></Button>
      <Dropdown :options="[{ label: 'Logout', icon: LogOut, onClick: handleLogout }]">
        <template #default>
          <button class="flex items-center gap-2 p-1 px-2 rounded-full hover:bg-gray-50 transition-colors">
            <Avatar label="Seller" size="md" class="border-2 border-white shadow-sm" />
          </button>
        </template>
      </Dropdown>
    </div>
  </nav>
</template>