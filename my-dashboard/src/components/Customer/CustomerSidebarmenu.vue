<script setup lang="ts">
import { ref, computed } from 'vue'
import { 
  createResource, 
  LoadingIndicator, 
  Avatar, 
  Button 
} from 'frappe-ui'
import { 
  MapPin, 
  Building, 
  Layers, 
  Store, 
  FilterX,
  ChevronRight,
  ChevronDown,
  X
} from 'lucide-vue-next'

interface Option { label: string; value: string }
interface SidebarData {
  customer: { name: string; customer_name: string } | null
  pincode_list: Option[]
  pincode_map: Record<string, { societies: Option[], sellers: Option[] }>
  all_categories: Option[]
}

const props = defineProps<{ isOpen?: boolean }>()
const emit = defineEmits(['update:filters', 'close'])

const expandedPincode = ref<string>('')
const expandedSociety = ref<string>('')
const expandedCategory = ref<string>('')
const selectedSeller = ref<string>('')

const sidebarData = createResource({
  url: 'my_frappe_app.api.get_customer_sidebar_data',
  auto: true,
  onSuccess(data: SidebarData) {
    if (data.pincode_list?.length > 0) {
      expandedPincode.value = data.pincode_list[0].value
    }
  }
})

const pincodeOptions = computed(() => (sidebarData.data as SidebarData)?.pincode_list || [])
const societyOptions = computed(() => {
  const map = (sidebarData.data as SidebarData)?.pincode_map
  return map?.[expandedPincode.value]?.societies || []
})
const categoryOptions = computed(() => (sidebarData.data as SidebarData)?.all_categories || [])
const sellerOptions = computed(() => {
  const map = (sidebarData.data as SidebarData)?.pincode_map
  return map?.[expandedPincode.value]?.sellers || []
})

const updateFilters = (sellerId: string = '') => {
  selectedSeller.value = sellerId
  emit('update:filters', {
    pincode: expandedPincode.value,
    society: expandedSociety.value,
    category: expandedCategory.value,
    seller: sellerId,
    customer: (sidebarData.data as SidebarData)?.customer?.name || ''
  })
  // Close sidebar on mobile after selection
  if (window.innerWidth < 768) emit('close')
}

const resetSelection = () => {
  expandedSociety.value = ''
  expandedCategory.value = ''
  selectedSeller.value = ''
  updateFilters('')
}
</script>

<template>
  <div 
    v-if="isOpen" 
    class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden" 
    @click="emit('close')"
  ></div>

  <div 
    :class="[
      'flex flex-col bg-white w-72 h-full border-r border-gray-100 transition-transform duration-300 z-50',
      'fixed inset-y-0 left-0 md:sticky md:top-0',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
    ]"
  >
    <div class="p-4 md:p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
      <div class="flex items-center gap-3">
        <Avatar
          :label="(sidebarData.data as SidebarData)?.customer?.customer_name || 'C'"
          size="lg" shape="square" class="ring-2 ring-white shadow-sm"
        />
        <div class="overflow-hidden">
          <h3 class="font-black text-gray-900 truncate text-sm">
            {{ (sidebarData.data as SidebarData)?.customer?.customer_name || 'User' }}
          </h3>
          <p class="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Shopping Portal</p>
        </div>
      </div>
      <button @click="emit('close')" class="md:hidden p-2 text-gray-400">
        <X class="w-5 h-5" />
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 custom-scrollbar">
      <div v-if="sidebarData.loading" class="flex justify-center py-10">
        <LoadingIndicator />
      </div>

      <div v-else class="space-y-1">
        <div v-for="pin in pincodeOptions" :key="pin.value" class="mb-1">
          <button 
            @click="expandedPincode = expandedPincode === pin.value ? '' : pin.value"
            class="w-full flex items-center gap-2 px-3 py-2 rounded-md hover:bg-gray-50 transition-all text-sm font-semibold"
            :class="expandedPincode === pin.value ? 'bg-gray-50 text-blue-600' : 'text-gray-700'"
          >
            <component :is="expandedPincode === pin.value ? ChevronDown : ChevronRight" class="w-4 h-4" />
            <MapPin class="w-4 h-4" />
            <span class="truncate">{{ pin.label }}</span>
          </button>

          <div v-if="expandedPincode === pin.value" class="ml-4 pl-3 border-l-2 border-gray-50 mt-1 space-y-1">
            <div v-for="soc in societyOptions" :key="soc.value">
              <button 
                @click="expandedSociety = expandedSociety === soc.value ? '' : soc.value"
                class="w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-gray-50 text-xs font-medium"
                :class="expandedSociety === soc.value ? 'bg-gray-50 text-gray-900' : 'text-gray-500'"
              >
                <component :is="expandedSociety === soc.value ? ChevronDown : ChevronRight" class="w-3.5 h-3.5" />
                <Building class="w-3.5 h-3.5" />
                <span class="truncate">{{ soc.label }}</span>
              </button>

              <div v-if="expandedSociety === soc.value" class="ml-4 pl-3 border-l-2 border-gray-50 mt-1 space-y-1">
                <div v-for="cat in categoryOptions" :key="cat.value">
                  <button 
                    @click="expandedCategory = expandedCategory === cat.value ? '' : cat.value"
                    class="w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-gray-50 text-[11px] font-medium"
                    :class="expandedCategory === cat.value ? 'text-gray-900' : 'text-gray-400'"
                  >
                    <component :is="expandedCategory === cat.value ? ChevronDown : ChevronRight" class="w-3 h-3" />
                    <Layers class="w-3.5 h-3.5" />
                    <span class="truncate">{{ cat.label }}</span>
                  </button>

                  <div v-if="expandedCategory === cat.value" class="ml-4 pl-2 mt-1 space-y-1">
                    <button 
                      v-for="sel in sellerOptions" :key="sel.value"
                      @click="updateFilters(sel.value)"
                      class="w-full text-left flex items-center gap-2 px-3 py-2 rounded-md text-[11px] transition-all"
                      :class="selectedSeller === sel.value ? 'bg-blue-600 text-white shadow-md font-bold' : 'hover:bg-gray-50 text-gray-500'"
                    >
                      <Store class="w-3 h-3 flex-shrink-0" />
                      <span class="truncate">{{ sel.label }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="p-4 border-t border-gray-100 bg-gray-50/30">
      <Button 
        v-if="selectedSeller" variant="subtle" theme="gray" 
        class="w-full flex justify-center hover:text-red-600" @click="resetSelection"
      >
        <template #prefix><FilterX class="w-4 h-4" /></template>
        Clear Filters
      </Button>
      <p v-else class="text-center text-[10px] text-gray-400 font-medium">Select a seller to browse</p>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #f3f4f6; border-radius: 10px; }
</style>