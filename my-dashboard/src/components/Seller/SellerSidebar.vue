<script setup lang="ts">
import { ref, computed } from 'vue'
import { createResource, LoadingIndicator, Avatar, Button } from 'frappe-ui'
import { 
  MapPin, Building, Layers, Users, FilterX, 
  ChevronRight, ChevronDown, X 
} from 'lucide-vue-next'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['update:filters', 'close'])

// Fix for 'never' type errors
const expandedPincode = ref<string>('')
const expandedSociety = ref<string>('')
const expandedCategory = ref<string>('')
const selectedCustomer = ref<string>('')

const context = createResource({ url: 'my_frappe_app.api.get_seller_context', auto: true })
const options = createResource({
  url: 'my_frappe_app.api.get_filtered_options',
  makeParams() { return { pincode: expandedPincode.value } }
})
const categories = createResource({ url: 'my_frappe_app.api.get_item_categories', auto: true })

const selectCustomer = (val: string) => {
  selectedCustomer.value = val
  emit('update:filters', { customer: val })
  if (window.innerWidth < 1024) emit('close')
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 z-[60] lg:hidden backdrop-blur-sm" @click="emit('close')"></div>
  
  <aside :class="[
    'fixed inset-y-0 left-0 z-[70] w-72 bg-white border-r border-gray-100 flex flex-col transition-transform duration-300 lg:static lg:translate-x-0',
    isOpen ? 'translate-x-0' : '-translate-x-full'
  ]">
    <div class="p-4 border-b border-gray-50 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Avatar :label="context.data?.company?.company_name || 'S'" size="md" class="bg-gray-900 text-white" />
        <div class="leading-tight">
          <p class="text-sm font-black truncate w-40 text-gray-900">{{ context.data?.company?.company_name || 'Seller Admin' }}</p>
          <p class="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Explorer</p>
        </div>
      </div>
      <Button variant="ghost" class="lg:hidden" @click="emit('close')"><X class="w-4 h-4" /></Button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-1 custom-scrollbar">
      <div v-for="pin in context.data?.pincodes" :key="pin.value">
        <button @click="expandedPincode = expandedPincode === pin.value ? '' : pin.value; if(expandedPincode) options.fetch()" 
          class="w-full flex items-center gap-2 px-2 py-2 rounded-md hover:bg-gray-50 text-sm font-bold text-gray-700 transition-colors text-left">
          <component :is="expandedPincode === pin.value ? ChevronDown : ChevronRight" class="w-4 h-4 text-gray-300" />
          <MapPin class="w-4 h-4 text-blue-500" /> {{ pin.label }}
        </button>

        <div v-if="expandedPincode === pin.value" class="ml-4 pl-3 border-l border-gray-100 space-y-1 mt-1">
          <div v-for="soc in options.data?.societies" :key="soc.value">
            <button @click="expandedSociety = expandedSociety === soc.value ? '' : soc.value" 
              class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-gray-50 text-xs text-gray-600 text-left">
              <component :is="expandedSociety === soc.value ? ChevronDown : ChevronRight" class="w-3 h-3 text-gray-400" />
              <Building class="w-3.5 h-3.5 text-gray-400" /> {{ soc.label }}
            </button>

            <div v-if="expandedSociety === soc.value" class="ml-4 pl-3 border-l border-gray-100 space-y-1">
              <div v-for="cat in categories.data" :key="cat.value">
                <button @click="expandedCategory = expandedCategory === cat.value ? '' : cat.value" 
                  class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-gray-50 text-[11px] text-gray-500 text-left">
                  <component :is="expandedCategory === cat.value ? ChevronDown : ChevronRight" class="w-3 h-3 text-gray-400" />
                  <Layers class="w-3.5 h-3.5 text-gray-400" /> {{ cat.label }}
                </button>

                <div v-if="expandedCategory === cat.value" class="ml-4 pl-3 border-l border-gray-100 space-y-1">
                  <button v-for="cus in options.data?.customers" :key="cus.value" 
                    @click="selectCustomer(cus.value)"
                    :class="['w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] text-left transition-all', selectedCustomer === cus.value ? 'bg-blue-600 text-white font-bold shadow-lg shadow-blue-100' : 'text-gray-500 hover:bg-gray-50']">
                    <Users class="w-3 h-3" /> {{ cus.label }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>