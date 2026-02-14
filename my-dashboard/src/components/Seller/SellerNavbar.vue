<script setup lang="ts">
import { ref, inject, computed } from 'vue'
import { Dropdown, Avatar, Button } from 'frappe-ui'
import { LogOut, Menu, Bell, Layout, Users } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const emit = defineEmits(['toggle-sidebar'])

const handleLogout = async () => {
  try {
    await fetch('/api/method/logout', { method: 'POST' })
    window.location.href = '/login'
  } catch (e) {
    window.location.href = '/login'
  }
}

const userRole = inject<any>('userRole')
const router = useRouter()

const dropdownOptions = computed(() => [
  ...(userRole?.value === 'Administrator' ? [
    {
      label: 'Switch to Customer Portal',
      icon: Users,
      onClick: () => { router.push('/customer') }
    },
    {
      label: 'Go to Desk',
      icon: Layout,
      onClick: () => { window.location.href = '/app' }
    }
  ] : []),
  { label: 'Logout', icon: LogOut, onClick: handleLogout }
])
</script>

<template>
  <nav class="h-16 border-b bg-white/80 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-[50]">
    <div class="flex items-center gap-3">
      <Button variant="ghost" class="lg:hidden p-2" @click="emit('toggle-sidebar')">
        <Menu class="w-5 h-5 text-gray-600" />
      </Button>
      <div class="flex items-center gap-2">
        <div
          class="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center text-white font-black shadow-lg shadow-blue-100">
          S</div>
        <h1 class="font-black text-gray-900 text-lg tracking-tight hidden sm:block">Seller Portal</h1>
      </div>
    </div>

    <div class="flex items-center gap-4">
      <Button variant="ghost" class="p-2 text-gray-400 hover:bg-gray-50">
        <Bell class="w-5 h-5" />
      </Button>
      <Dropdown :options="dropdownOptions">
        <template #default>
          <button class="flex items-center gap-2 p-1 px-2 rounded-full hover:bg-gray-50 transition-colors">
            <Avatar label="Seller" size="md" class="border-2 border-white shadow-sm" />
          </button>
        </template>
      </Dropdown>
    </div>
  </nav>
</template>