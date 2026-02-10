<script setup lang="ts">
import CrmSidebar from '@/components/CrmSidebar.vue'
import UserList from '@/components/UserList.vue';


</script>

<template>
  <div class="flex h-screen w-full bg-white text-gray-900">
    <div class="w-[220px] border-r h-full flex-shrink-0">
      <CrmSidebar />
    </div>
    <div class="flex-1 p-6 overflow-hidden flex flex-col">
      <UserList />
    </div>
  </div>
</template>