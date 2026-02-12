<script setup lang="ts">
import { ref } from 'vue'
import { Dropdown, Avatar, Button } from 'frappe-ui'
import { LogOut, Menu } from 'lucide-vue-next'

const emit = defineEmits(['toggle-sidebar'])

const session = ref({
  user_fullname: (window as any).frappe?.session?.user_fullname || 'User'
})

const handleLogout = async () => {
  try {
    await fetch('/api/method/logout', { method: 'POST' })
    window.location.href = '/login'
  } catch (e) {
    window.location.href = '/login'
  }
}

const options = [{ label: 'Logout', icon: LogOut, onClick: handleLogout }]
</script>

<template>
  <nav class="h-14 border-b bg-white flex items-center justify-between px-4 sticky top-0 z-30">
    <div class="flex items-center gap-2">
      <Button variant="ghost" class="lg:hidden" @click="emit('toggle-sidebar')">
        <Menu class="w-5 h-5" />
      </Button>
      <h1 class="font-bold text-gray-800 text-lg">Seller Portal</h1>
    </div>

    <Dropdown :options="options">
      <Button variant="ghost" class="flex items-center gap-2">
        <span class="hidden sm:block text-sm font-medium text-gray-600">
          {{ session.user_fullname }}
        </span>
        <Avatar :label="session.user_fullname" size="sm" />
      </Button>
    </Dropdown>
  </nav>
</template>