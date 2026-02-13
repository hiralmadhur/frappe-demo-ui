<script setup lang="ts">
import { ref } from 'vue'
import { createResource, Avatar, Button } from 'frappe-ui'
import { MapPin, Building, Users, ChevronRight, ChevronDown, X, FilterX } from 'lucide-vue-next'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['update:filters', 'close'])

const expandedPin = ref<string | null>(null)
const selectedCus = ref<string | null>(null)

// API Resources
const context = createResource({ url: 'my_frappe_app.api.get_seller_context', auto: true })
const options = createResource({
  url: 'my_frappe_app.api.get_filtered_options',
  makeParams() { return { pincode: expandedPin.value } }
})

const selectCustomer = (val: string) => {
  selectedCus.value = val
  emit('update:filters', { customer: val })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 z-[100] lg:hidden backdrop-blur-sm" @click="emit('close')"></div>
  
  <aside :class="['fixed inset-y-0 left-0 z-[110] w-72 bg-white flex flex-col transition-transform duration-300 lg:static lg:translate-x-0 border-r border-gray-100', 
    isOpen ? 'translate-x-0' : '-translate-x-full']">
    
    <div class="p-4 h-16 border-b flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Avatar :label="context.data?.company?.company_name || 'S'" size="md" class="bg-gray-900" />
        <div class="truncate leading-tight">
          <p class="text-sm font-black text-gray-900 truncate">{{ context.data?.company?.company_name || 'Gokuldham' }}</p>
          <p class="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Explorer</p>
        </div>
      </div>
      <Button variant="ghost" class="lg:hidden" @click="emit('close')"><X class="w-4 h-4" /></Button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-1 custom-scrollbar">
      <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4 px-2">Select Hierarchy</p>
      
      <div v-for="pin in context.data?.pincodes" :key="pin.value">
        <button @click="expandedPin = expandedPin === pin.value ? null : pin.value; if(expandedPin) options.fetch()" 
          class="w-full flex items-center gap-2 p-2 hover:bg-gray-50 rounded text-sm font-bold text-gray-700">
          <component :is="expandedPin === pin.value ? ChevronDown : ChevronRight" class="w-4 h-4 text-gray-300" />
          <MapPin class="w-4 h-4 text-blue-500" /> {{ pin.label }}
        </button>

        <div v-if="expandedPin === pin.value" class="ml-4 pl-3 border-l border-gray-100 space-y-1 mt-1">
          <button v-for="cus in options.data?.customers" :key="cus.value" @click="selectCustomer(cus.value)"
            :class="['w-full flex items-center gap-2 p-2 rounded text-xs transition-all text-left', 
            selectedCus === cus.value ? 'bg-blue-600 text-white font-bold shadow-lg' : 'text-gray-500 hover:bg-gray-50']">
            <Users class="w-3.5 h-3.5" /> {{ cus.label }}
          </button>
        </div>
      </div>
    </div>

    <div class="p-4 border-t border-gray-50">
      <Button variant="subtle" theme="gray" class="w-full" @click="selectedCus = null; emit('update:filters', {})">
        <template #prefix><FilterX class="w-4 h-4" /></template> Clear Filters
      </Button>
    </div>
  </aside>
</template>