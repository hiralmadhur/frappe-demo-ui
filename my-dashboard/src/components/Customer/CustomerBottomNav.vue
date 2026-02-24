<script setup lang="ts">
import { Store, ClipboardList, Newspaper } from 'lucide-vue-next'

const props = defineProps<{
  activeTab: string
  orderCount?: number
  subCount?: number
}>()

const emit = defineEmits<{
  (e: 'change-tab', tab: string): void
}>()

const tabs = [
  { key: 'shop',          label: 'Shop',    icon: Store },
  { key: 'orders',        label: 'Orders',  icon: ClipboardList },
  { key: 'subscriptions', label: 'Plans',   icon: Newspaper },
]
</script>

<template>
  <!-- Only mobile me show hoga — md aur upar pe hidden -->
  <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100
               flex items-center z-50 md:hidden"
       style="padding-bottom: env(safe-area-inset-bottom)">

    <button
      v-for="tab in tabs"
      :key="tab.key"
      @click="emit('change-tab', tab.key)"
      :class="[
        'flex-1 flex flex-col items-center py-3 gap-1 transition-all relative',
        activeTab === tab.key ? 'text-blue-600' : 'text-gray-400'
      ]"
    >
      <!-- Active indicator bar top pe -->
      <div
        v-if="activeTab === tab.key"
        class="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-blue-600 rounded-full"
      />

      <!-- Badge for orders/plans count -->
      <div class="relative">
        <component :is="tab.icon" class="w-5 h-5" />
        <span
          v-if="tab.key === 'orders' && orderCount && orderCount > 0"
          class="absolute -top-1.5 -right-1.5 w-4 h-4 bg-blue-600 text-white text-[9px] font-bold rounded-full flex items-center justify-center"
        >
          {{ orderCount > 9 ? '9+' : orderCount }}
        </span>
        <span
          v-if="tab.key === 'subscriptions' && subCount && subCount > 0"
          class="absolute -top-1.5 -right-1.5 w-4 h-4 bg-green-600 text-white text-[9px] font-bold rounded-full flex items-center justify-center"
        >
          {{ subCount > 9 ? '9+' : subCount }}
        </span>
      </div>

      <span class="text-[10px] font-semibold">{{ tab.label }}</span>
    </button>
  </nav>
</template>